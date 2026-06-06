#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/twist.hpp>
#include <geometry_msgs/msg/transform_stamped.hpp>
#include <nav_msgs/msg/odometry.hpp>
#include <tf2/LinearMath/Quaternion.h>
#include <tf2_ros/transform_broadcaster.h>

#include <fcntl.h>
#include <termios.h>
#include <unistd.h>

#include <algorithm>
#include <cmath>
#include <string>

class ArduinoBridge : public rclcpp::Node
{
public:
    ArduinoBridge()
    : Node("arduino_bridge"),
      x_(0.0), y_(0.0), theta_(0.0),
      vx_(0.0), wz_(0.0),
      first_read_(true),
      initial_yaw_(0.0),
      filtered_yaw_(0.0),
      prev_theta_(0.0)
    {
        odom_pub_ = this->create_publisher<nav_msgs::msg::Odometry>("odom", 10);
        tf_broadcaster_ = std::make_unique<tf2_ros::TransformBroadcaster>(*this);

        cmd_vel_sub_ = this->create_subscription<geometry_msgs::msg::Twist>(
            "cmd_vel", 10,
            std::bind(&ArduinoBridge::cmd_vel_callback, this, std::placeholders::_1));

        open_serial_port("/dev/arduino_mega", B115200);

        timer_ = this->create_wall_timer(
            std::chrono::milliseconds(10),
            std::bind(&ArduinoBridge::read_serial_and_publish_odom, this));

        RCLCPP_INFO(this->get_logger(), "Arduino bridge ready: publish /odom and TF odom -> base_footprint");
    }

    ~ArduinoBridge()
    {
        if (serial_fd_ != -1) {
            close(serial_fd_);
        }
    }

private:
    int serial_fd_{-1};
    std::string serial_buffer_;

    // Khoảng cách ứng với 1 xung encoder, giữ theo cấu hình hiện tại của bạn.
    static constexpr double D_P = 0.000055185;
    static constexpr double PI = 3.14159265358979323846;

    // Lọc yaw BNO055 để giảm giật TF khi mapping 3D.
    // alpha càng cao càng bám nhanh nhưng dễ giật hơn. 0.20-0.35 phù hợp để thử.
    static constexpr double YAW_FILTER_ALPHA = 0.25;
    static constexpr double YAW_DEADBAND_RAD = 0.0015;  // ~0.086 độ

    double x_;
    double y_;
    double theta_;
    double vx_;
    double wz_;
    bool first_read_;
    double initial_yaw_;
    double filtered_yaw_;
    double prev_theta_;
    rclcpp::Time last_odom_time_;

    long last_pos_left_{0};
    long last_pos_right_{0};

    rclcpp::Publisher<nav_msgs::msg::Odometry>::SharedPtr odom_pub_;
    rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr cmd_vel_sub_;
    std::unique_ptr<tf2_ros::TransformBroadcaster> tf_broadcaster_;
    rclcpp::TimerBase::SharedPtr timer_;

    static double normalize_angle(double a)
    {
        while (a > PI) a -= 2.0 * PI;
        while (a < -PI) a += 2.0 * PI;
        return a;
    }

    static double shortest_angle_delta(double from, double to)
    {
        return normalize_angle(to - from);
    }

    void open_serial_port(const std::string &port_name, int baud_rate)
    {
        serial_fd_ = open(port_name.c_str(), O_RDWR | O_NOCTTY | O_NDELAY);
        if (serial_fd_ == -1) {
            RCLCPP_ERROR(this->get_logger(), "Cannot open serial port: %s", port_name.c_str());
            return;
        }

        termios options{};
        tcgetattr(serial_fd_, &options);
        cfsetispeed(&options, baud_rate);
        cfsetospeed(&options, baud_rate);

        options.c_cflag |= (CLOCAL | CREAD);
        options.c_cflag &= ~PARENB;
        options.c_cflag &= ~CSTOPB;
        options.c_cflag &= ~CSIZE;
        options.c_cflag |= CS8;
        options.c_lflag &= ~(ICANON | ECHO | ECHOE | ISIG);
        options.c_oflag &= ~OPOST;
        options.c_iflag &= ~(IXON | IXOFF | IXANY);

        tcsetattr(serial_fd_, TCSANOW, &options);
        tcflush(serial_fd_, TCIOFLUSH);
    }

    void cmd_vel_callback(const geometry_msgs::msg::Twist::SharedPtr msg)
    {
        if (serial_fd_ == -1) return;

        std::string command = std::to_string(msg->linear.x) + "," +
                              std::to_string(msg->angular.z) + "\n";
        write(serial_fd_, command.c_str(), command.length());
    }

    void read_serial_and_publish_odom()
    {
        if (serial_fd_ == -1) return;

        char buf[256];
        int n = read(serial_fd_, buf, sizeof(buf) - 1);
        if (n <= 0) return;

        buf[n] = '\0';
        serial_buffer_ += buf;

        size_t pos;
        while ((pos = serial_buffer_.find('\n')) != std::string::npos) {
            std::string line = serial_buffer_.substr(0, pos);
            serial_buffer_.erase(0, pos + 1);
            process_sensor_data(line);
        }

        // Tránh buffer phình nếu serial lỗi không có \n.
        if (serial_buffer_.size() > 1024) {
            serial_buffer_.clear();
            RCLCPP_WARN(this->get_logger(), "Serial buffer overflow, cleared");
        }
    }

    void process_sensor_data(const std::string &data)
    {
        // Format mong đợi: e:left_ticks,right_ticks,yaw_deg
        if (data.rfind("e:", 0) != 0) {
            return;
        }

        try {
            std::string payload = data.substr(2);
            size_t comma1 = payload.find(',');
            size_t comma2 = payload.find(',', comma1 + 1);
            if (comma1 == std::string::npos || comma2 == std::string::npos) {
                return;
            }

            long pos_left = std::stol(payload.substr(0, comma1));
            long pos_right = std::stol(payload.substr(comma1 + 1, comma2 - comma1 - 1));
            double yaw_deg = std::stod(payload.substr(comma2 + 1));
            double raw_yaw = yaw_deg * PI / 180.0;

            rclcpp::Time now = this->get_clock()->now();

            if (first_read_) {
                last_pos_left_ = pos_left;
                last_pos_right_ = pos_right;
                initial_yaw_ = raw_yaw;
                filtered_yaw_ = 0.0;
                theta_ = 0.0;
                prev_theta_ = 0.0;
                last_odom_time_ = now;
                first_read_ = false;
                return;
            }

            long delta_l_ticks = pos_left - last_pos_left_;
            long delta_r_ticks = pos_right - last_pos_right_;
            last_pos_left_ = pos_left;
            last_pos_right_ = pos_right;

            double d_l = static_cast<double>(delta_l_ticks) * D_P;
            double d_r = static_cast<double>(delta_r_ticks) * D_P;
            double d_center = 0.5 * (d_l + d_r);

            double yaw_measure = normalize_angle(raw_yaw - initial_yaw_);

            // Low-pass yaw theo delta ngắn nhất để không lỗi tại ±pi.
            double dyaw = shortest_angle_delta(filtered_yaw_, yaw_measure);
            if (std::abs(dyaw) < YAW_DEADBAND_RAD) {
                dyaw = 0.0;
            }
            filtered_yaw_ = normalize_angle(filtered_yaw_ + YAW_FILTER_ALPHA * dyaw);
            theta_ = filtered_yaw_;

            double dt = (now - last_odom_time_).seconds();
            if (dt > 0.002 && dt < 1.0) {
                vx_ = d_center / dt;
                double dtheta = shortest_angle_delta(prev_theta_, theta_);
                wz_ = dtheta / dt;
            } else {
                vx_ = 0.0;
                wz_ = 0.0;
            }
            last_odom_time_ = now;
            prev_theta_ = theta_;

            x_ += d_center * std::cos(theta_);
            y_ += d_center * std::sin(theta_);

            publish_tf_and_odom(now);
        } catch (const std::exception &e) {
            RCLCPP_WARN(this->get_logger(), "Bad serial packet ignored: %s", e.what());
        }
    }

    void publish_tf_and_odom(const rclcpp::Time &stamp)
    {
        tf2::Quaternion q;
        q.setRPY(0.0, 0.0, theta_);
        q.normalize();

        geometry_msgs::msg::TransformStamped tf_msg;
        tf_msg.header.stamp = stamp;  // Không publish TF tương lai.
        tf_msg.header.frame_id = "odom";
        tf_msg.child_frame_id = "base_footprint";
        tf_msg.transform.translation.x = x_;
        tf_msg.transform.translation.y = y_;
        tf_msg.transform.translation.z = 0.0;
        tf_msg.transform.rotation.x = q.x();
        tf_msg.transform.rotation.y = q.y();
        tf_msg.transform.rotation.z = q.z();
        tf_msg.transform.rotation.w = q.w();
        tf_broadcaster_->sendTransform(tf_msg);

        nav_msgs::msg::Odometry odom;
        odom.header.stamp = stamp;
        odom.header.frame_id = "odom";
        odom.child_frame_id = "base_footprint";
        odom.pose.pose.position.x = x_;
        odom.pose.pose.position.y = y_;
        odom.pose.pose.position.z = 0.0;
        odom.pose.pose.orientation = tf_msg.transform.rotation;

        odom.twist.twist.linear.x = vx_;
        odom.twist.twist.linear.y = 0.0;
        odom.twist.twist.angular.z = wz_;

        // Covariance để các node khác không hiểu odom là tuyệt đối hoàn hảo.
        odom.pose.covariance[0] = 0.02;     // x
        odom.pose.covariance[7] = 0.02;     // y
        odom.pose.covariance[14] = 1e6;     // z
        odom.pose.covariance[21] = 1e6;     // roll
        odom.pose.covariance[28] = 1e6;     // pitch
        odom.pose.covariance[35] = 0.08;    // yaw

        odom.twist.covariance[0] = 0.03;    // vx
        odom.twist.covariance[7] = 1e6;     // vy
        odom.twist.covariance[14] = 1e6;    // vz
        odom.twist.covariance[21] = 1e6;    // vroll
        odom.twist.covariance[28] = 1e6;    // vpitch
        odom.twist.covariance[35] = 0.10;   // wz

        odom_pub_->publish(odom);
    }
};

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<ArduinoBridge>());
    rclcpp::shutdown();
    return 0;
}
