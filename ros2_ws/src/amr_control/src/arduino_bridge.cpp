#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/twist.hpp>
#include <nav_msgs/msg/odometry.hpp>
#include <sensor_msgs/msg/imu.hpp>
#include <tf2/LinearMath/Quaternion.h>

#include <fcntl.h>
#include <termios.h>
#include <unistd.h>

#include <cmath>
#include <sstream>
#include <string>
#include <vector>

class ArduinoBridge : public rclcpp::Node
{
public:
    ArduinoBridge()
    : Node("arduino_bridge")
    {
        serial_port_ = this->declare_parameter<std::string>("serial_port", "/dev/arduino_mega");
        //distance_per_tick_ = this->declare_parameter<double>("distance_per_tick", 0.000054245);
        distance_per_tick_ = this->declare_parameter<double>("distance_per_tick", 0.000055185);
        wheel_separation_ = this->declare_parameter<double>("wheel_separation", 0.33);
        encoder_yaw_sign_ = this->declare_parameter<double>("encoder_yaw_sign", 1.0);

        imu_yaw_filter_alpha_ = this->declare_parameter<double>("imu_yaw_filter_alpha", 0.25);
        imu_yaw_deadband_rad_ = this->declare_parameter<double>("imu_yaw_deadband_rad", 0.0015);

        wheel_odom_pub_ = this->create_publisher<nav_msgs::msg::Odometry>("/wheel/odom", 10);
        imu_pub_ = this->create_publisher<sensor_msgs::msg::Imu>("/imu/data", 10);

        // Giữ tên topic nội bộ là "cmd_vel" để bringup_fusion.launch.py remap sang /cmd_vel_safe như hiện tại.
        cmd_vel_sub_ = this->create_subscription<geometry_msgs::msg::Twist>(
            "cmd_vel", 10,
            std::bind(&ArduinoBridge::cmd_vel_callback, this, std::placeholders::_1));

        open_serial_port(serial_port_, B115200);

        timer_ = this->create_wall_timer(
            std::chrono::milliseconds(10),
            std::bind(&ArduinoBridge::read_serial_and_publish, this));

        RCLCPP_INFO(
            this->get_logger(),
            "Arduino bridge EKF-step1 ready: publish /wheel/odom + /imu/data, NO odom->base_footprint TF");
    }

    ~ArduinoBridge()
    {
        if (serial_fd_ != -1) {
            close(serial_fd_);
        }
    }

private:
    static constexpr double PI = 3.14159265358979323846;

    int serial_fd_{-1};
    std::string serial_port_;
    std::string serial_buffer_;

    //double distance_per_tick_{0.000054245};
    double distance_per_tick_{0.000055185}; 
    double wheel_separation_{0.33};
    double encoder_yaw_sign_{1.0};

    double imu_yaw_filter_alpha_{0.25};
    double imu_yaw_deadband_rad_{0.0015};

    bool first_read_{true};
    long last_left_ticks_{0};
    long last_right_ticks_{0};
    rclcpp::Time last_stamp_;

    // Wheel-only odometry state. This is deliberately NOT fused with IMU yaw.
    double wheel_x_{0.0};
    double wheel_y_{0.0};
    double wheel_yaw_{0.0};

    // IMU yaw state, zeroed at first packet.
    double initial_yaw_{0.0};
    double imu_yaw_filtered_{0.0};
    double prev_imu_yaw_filtered_{0.0};

    rclcpp::Publisher<nav_msgs::msg::Odometry>::SharedPtr wheel_odom_pub_;
    rclcpp::Publisher<sensor_msgs::msg::Imu>::SharedPtr imu_pub_;
    rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr cmd_vel_sub_;
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

    static std::vector<std::string> split_csv(const std::string &s)
    {
        std::vector<std::string> out;
        std::stringstream ss(s);
        std::string item;
        while (std::getline(ss, item, ',')) {
            out.push_back(item);
        }
        return out;
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
        if (serial_fd_ == -1) {
            return;
        }

        std::string command =
            std::to_string(msg->linear.x) + "," +
            std::to_string(msg->angular.z) + "\n";

        write(serial_fd_, command.c_str(), command.length());
    }

    void read_serial_and_publish()
    {
        if (serial_fd_ == -1) {
            return;
        }

        char buf[256];
        int n = read(serial_fd_, buf, sizeof(buf) - 1);
        if (n <= 0) {
            return;
        }

        buf[n] = '\0';
        serial_buffer_ += buf;

        size_t pos;
        while ((pos = serial_buffer_.find('\n')) != std::string::npos) {
            std::string line = serial_buffer_.substr(0, pos);
            serial_buffer_.erase(0, pos + 1);
            process_sensor_data(line);
        }

        if (serial_buffer_.size() > 1024) {
            serial_buffer_.clear();
            RCLCPP_WARN(this->get_logger(), "Serial buffer overflow, cleared");
        }
    }

    void process_sensor_data(const std::string &data)
    {
        // Hỗ trợ 2 format:
        //   e:left_ticks,right_ticks,yaw_deg
        //   e:left_ticks,right_ticks,yaw_deg,gyro_z_dps
        // Format hiện tại từ Arduino của bạn là format 3 giá trị.
        if (data.rfind("e:", 0) != 0) {
            return;
        }

        try {
            const std::string payload = data.substr(2);
            const auto fields = split_csv(payload);

            if (fields.size() < 3) {
                return;
            }

            const long left_ticks = std::stol(fields[0]);
            const long right_ticks = std::stol(fields[1]);
            const double yaw_deg = std::stod(fields[2]);
            const bool has_gyro_z = fields.size() >= 4;
            const double gyro_z_rad_s = has_gyro_z ? (std::stod(fields[3]) * PI / 180.0) : 0.0;

            const rclcpp::Time stamp = this->get_clock()->now();
            const double raw_yaw = yaw_deg * PI / 180.0;

            if (first_read_) {
                last_left_ticks_ = left_ticks;
                last_right_ticks_ = right_ticks;
                last_stamp_ = stamp;

                initial_yaw_ = raw_yaw;
                imu_yaw_filtered_ = 0.0;
                prev_imu_yaw_filtered_ = 0.0;

                wheel_x_ = 0.0;
                wheel_y_ = 0.0;
                wheel_yaw_ = 0.0;

                first_read_ = false;
                return;
            }

            const double dt = (stamp - last_stamp_).seconds();
            if (dt <= 0.002 || dt > 1.0) {
                last_stamp_ = stamp;
                last_left_ticks_ = left_ticks;
                last_right_ticks_ = right_ticks;
                return;
            }

            const long delta_left_ticks = left_ticks - last_left_ticks_;
            const long delta_right_ticks = right_ticks - last_right_ticks_;
            last_left_ticks_ = left_ticks;
            last_right_ticks_ = right_ticks;
            last_stamp_ = stamp;

            const double d_left = static_cast<double>(delta_left_ticks) * distance_per_tick_;
            const double d_right = static_cast<double>(delta_right_ticks) * distance_per_tick_;
            const double d_center = 0.5 * (d_left + d_right);

            // Encoder-only differential drive yaw.
            // Nếu test quay tại chỗ thấy dấu angular.z bị ngược, đổi encoder_yaw_sign thành -1.0 bằng parameter.
            const double d_yaw_encoder = encoder_yaw_sign_ * (d_right - d_left) / wheel_separation_;

            wheel_yaw_ = normalize_angle(wheel_yaw_ + d_yaw_encoder);
            wheel_x_ += d_center * std::cos(wheel_yaw_);
            wheel_y_ += d_center * std::sin(wheel_yaw_);

            const double wheel_vx = d_center / dt;
            const double wheel_wz = d_yaw_encoder / dt;

            // IMU yaw, zeroed at startup and lightly filtered.
            const double imu_yaw_measure = normalize_angle(raw_yaw - initial_yaw_);
            double imu_delta = shortest_angle_delta(imu_yaw_filtered_, imu_yaw_measure);
            if (std::abs(imu_delta) < imu_yaw_deadband_rad_) {
                imu_delta = 0.0;
            }

            prev_imu_yaw_filtered_ = imu_yaw_filtered_;
            imu_yaw_filtered_ = normalize_angle(imu_yaw_filtered_ + imu_yaw_filter_alpha_ * imu_delta);

            const double imu_wz_derived = shortest_angle_delta(prev_imu_yaw_filtered_, imu_yaw_filtered_) / dt;
            const double imu_wz = has_gyro_z ? gyro_z_rad_s : imu_wz_derived;

            publish_wheel_odom(stamp, wheel_vx, wheel_wz);
            publish_imu(stamp, imu_wz, has_gyro_z);
        } catch (const std::exception &e) {
            RCLCPP_WARN(this->get_logger(), "Bad serial packet ignored: %s", e.what());
        }
    }

    void publish_wheel_odom(const rclcpp::Time &stamp, double wheel_vx, double wheel_wz)
    {
        tf2::Quaternion q;
        q.setRPY(0.0, 0.0, wheel_yaw_);
        q.normalize();

        nav_msgs::msg::Odometry odom;
        odom.header.stamp = stamp;
        odom.header.frame_id = "odom";
        odom.child_frame_id = "base_footprint";

        odom.pose.pose.position.x = wheel_x_;
        odom.pose.pose.position.y = wheel_y_;
        odom.pose.pose.position.z = 0.0;
        odom.pose.pose.orientation.x = q.x();
        odom.pose.pose.orientation.y = q.y();
        odom.pose.pose.orientation.z = q.z();
        odom.pose.pose.orientation.w = q.w();

        odom.twist.twist.linear.x = wheel_vx;
        odom.twist.twist.linear.y = 0.0;
        odom.twist.twist.angular.z = wheel_wz;

        // Pose encoder-only không nên tin tuyệt đối; EKF giai đoạn đầu sẽ ưu tiên twist.
        odom.pose.covariance[0] = 0.20;     // x
        odom.pose.covariance[7] = 0.20;     // y
        odom.pose.covariance[14] = 1e6;     // z
        odom.pose.covariance[21] = 1e6;     // roll
        odom.pose.covariance[28] = 1e6;     // pitch
        odom.pose.covariance[35] = 0.50;    // yaw

        odom.twist.covariance[0] = 0.03;    // vx
        odom.twist.covariance[7] = 0.001;   // vy=0 constraint for non-holonomic robot
        odom.twist.covariance[14] = 1e6;    // vz
        odom.twist.covariance[21] = 1e6;    // vroll
        odom.twist.covariance[28] = 1e6;    // vpitch
        odom.twist.covariance[35] = 0.20;   // wz encoder

        wheel_odom_pub_->publish(odom);
    }

    void publish_imu(const rclcpp::Time &stamp, double imu_wz, bool has_real_gyro_z)
    {
        tf2::Quaternion q;
        q.setRPY(0.0, 0.0, imu_yaw_filtered_);
        q.normalize();

        sensor_msgs::msg::Imu imu;
        imu.header.stamp = stamp;
        imu.header.frame_id = "imu_link";

        imu.orientation.x = q.x();
        imu.orientation.y = q.y();
        imu.orientation.z = q.z();
        imu.orientation.w = q.w();

        imu.angular_velocity.x = 0.0;
        imu.angular_velocity.y = 0.0;
        imu.angular_velocity.z = imu_wz;

        imu.linear_acceleration.x = 0.0;
        imu.linear_acceleration.y = 0.0;
        imu.linear_acceleration.z = 0.0;

        // Chỉ yaw đáng dùng; roll/pitch đặt covariance rất lớn.
        // Giảm covariance yaw và angular velocity để EKF tin tưởng IMU cao:
        //   orientation[8]  = 0.005 : BNO055 absolute yaw ~2-3° sai số → tin cao (R nhỏ → K lớn)
        //   angular_vel[8]  = 0.01  (real gyro_z) / 0.05 (derived từ đạo hàm yaw)
        imu.orientation_covariance[0] = 1e6;    // roll  (không dùng)
        imu.orientation_covariance[4] = 1e6;    // pitch (không dùng)
        imu.orientation_covariance[8] = 0.005;  // yaw   ← tin cao (giảm từ 0.08)

        imu.angular_velocity_covariance[0] = 1e6;
        imu.angular_velocity_covariance[4] = 1e6;
        imu.angular_velocity_covariance[8] = has_real_gyro_z ? 0.01 : 0.05;
        //   real gyro_z BNO055: 0.01 (tin cao)
        //   derived từ đạo hàm yaw: 0.05 (tin vừa phải, nhiễu hơn)

        // Không dùng linear acceleration ở giai đoạn đầu.
        imu.linear_acceleration_covariance[0] = -1.0;

        imu_pub_->publish(imu);
    }
};

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<ArduinoBridge>());
    rclcpp::shutdown();
    return 0;
}