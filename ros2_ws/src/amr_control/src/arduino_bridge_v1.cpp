#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/twist.hpp>
#include <nav_msgs/msg/odometry.hpp>
#include <tf2/LinearMath/Quaternion.h>

#include <fcntl.h>
#include <termios.h>
#include <unistd.h>
#include <string>
#include <cmath>

class ArduinoBridge : public rclcpp::Node
{
public:
    ArduinoBridge() : Node("arduino_bridge"), x_(0.0), y_(0.0), theta_(0.0), first_read_(true), initial_yaw_(0.0), last_yaw_(0.0)
    {
        odom_pub_ = this->create_publisher<nav_msgs::msg::Odometry>("odom", 10);

        cmd_vel_sub_ = this->create_subscription<geometry_msgs::msg::Twist>(
            "cmd_vel", 10, std::bind(&ArduinoBridge::cmd_vel_callback, this, std::placeholders::_1));

        open_serial_port("/dev/arduino_mega", B115200);

        timer_ = this->create_wall_timer(
            std::chrono::milliseconds(33), 
            std::bind(&ArduinoBridge::read_serial_and_publish_odom, this));

        // Khởi tạo thời gian cho lần đo đầu tiên
        last_time_ = this->get_clock()->now();

        RCLCPP_INFO(this->get_logger(), "🚀 Cầu nối C++ (Chế độ UKF) đã sẵn sàng!");
    }

    ~ArduinoBridge()
    {
        if (serial_fd_ != -1) close(serial_fd_);
    }

private:
    int serial_fd_;
    std::string serial_buffer_ = "";
    
    const double D_P = 0.000055185; 
    const double PI = 3.14159265359;

    double x_, y_, theta_;
    long last_pos_left_ = 0;
    long last_pos_right_ = 0;
    bool first_read_;
    double initial_yaw_; 
    
    // Thêm các biến để tính Vận tốc
    rclcpp::Time last_time_;
    double last_yaw_;

    rclcpp::Publisher<nav_msgs::msg::Odometry>::SharedPtr odom_pub_;
    rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr cmd_vel_sub_;
    rclcpp::TimerBase::SharedPtr timer_;

    void open_serial_port(const std::string &port_name, int baud_rate)
    {
        serial_fd_ = open(port_name.c_str(), O_RDWR | O_NOCTTY | O_NDELAY);
        if (serial_fd_ == -1) {
            RCLCPP_ERROR(this->get_logger(), "❌ Không thể mở cổng Serial: %s", port_name.c_str());
            return;
        }

        struct termios options;
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
        tcsetattr(serial_fd_, TCSANOW, &options);
    }

    void cmd_vel_callback(const geometry_msgs::msg::Twist::SharedPtr msg)
    {
        if (serial_fd_ == -1) return;
        std::string command = std::to_string(msg->linear.x) + "," + std::to_string(msg->angular.z) + "\n";
        write(serial_fd_, command.c_str(), command.length());
    }

    void read_serial_and_publish_odom()
    {
        if (serial_fd_ == -1) return;

        char buf[256];
        int n = read(serial_fd_, buf, sizeof(buf) - 1);
        
        if (n > 0) {
            buf[n] = '\0';
            serial_buffer_ += buf; 

            size_t pos;
            while ((pos = serial_buffer_.find('\n')) != std::string::npos) {
                std::string line = serial_buffer_.substr(0, pos);
                serial_buffer_.erase(0, pos + 1);
                process_sensor_data(line);
            }
        }
    }

    void process_sensor_data(const std::string& data)
    {
        if (data.rfind("e:", 0) == 0) {
            std::string payload = data.substr(2); 
            size_t comma1 = payload.find(',');
            size_t comma2 = payload.find(',', comma1 + 1);

            if (comma1 != std::string::npos && comma2 != std::string::npos) {
                try {
                    long pos_left = std::stol(payload.substr(0, comma1));
                    long pos_right = std::stol(payload.substr(comma1 + 1, comma2 - comma1 - 1));
                    float yaw_deg = std::stof(payload.substr(comma2 + 1));

                    double yaw_rad = yaw_deg * PI / 180.0; 

                    if (first_read_) {
                        last_pos_left_ = pos_left;
                        last_pos_right_ = pos_right;
                        initial_yaw_ = yaw_rad; 
                        last_yaw_ = 0.0;
                        first_read_ = false;
                    }

                    long delta_l = pos_left - last_pos_left_;
                    long delta_r = pos_right - last_pos_right_;
                    last_pos_left_ = pos_left;
                    last_pos_right_ = pos_right;

                    double d_l = delta_l * D_P;
                    double d_r = delta_r * D_P;
                    double d_center = (d_l + d_r) / 2.0;

                    double current_yaw = yaw_rad - initial_yaw_;

                    while (current_yaw > PI) current_yaw -= 2.0 * PI;
                    while (current_yaw < -PI) current_yaw += 2.0 * PI;

                    x_ += d_center * cos(current_yaw);
                    y_ += d_center * sin(current_yaw);
                    theta_ = current_yaw; 

                    // --- BỔ SUNG: Tính Vận tốc (Twist) cho UKF ---
                    rclcpp::Time current_time = this->get_clock()->now();
                    double dt = (current_time - last_time_).seconds();
                    
                    double vx = 0.0;
                    double vtheta = 0.0;
                    if (dt > 0.0) {
                        vx = d_center / dt;
                        
                        // Tính delta góc mượt mà chống nhảy 360 độ
                        double delta_theta = current_yaw - last_yaw_;
                        while (delta_theta > PI) delta_theta -= 2.0 * PI;
                        while (delta_theta < -PI) delta_theta += 2.0 * PI;
                        
                        vtheta = delta_theta / dt;
                    }
                    
                    last_time_ = current_time;
                    last_yaw_ = current_yaw;

                    // Gửi tọa độ và vận tốc
                    publish_odom(vx, vtheta);

                } catch (const std::exception& e) {
                    RCLCPP_WARN(this->get_logger(), "Nhiễu Serial, bỏ qua gói tin lỗi...");
                }
            }
        }
    }

    void publish_odom(double vx, double vtheta)
    {
        rclcpp::Time now = this->get_clock()->now();

        tf2::Quaternion q;
        q.setRPY(0, 0, theta_);

        // KHÔNG CÒN BẮN TF Ở ĐÂY NỮA (Đã nhường cho UKF)

        // Bắn Odom Topic (Cho UKF tiêu thụ)
        nav_msgs::msg::Odometry odom;
        odom.header.stamp = now;
        odom.header.frame_id = "odom";
        odom.child_frame_id = "base_footprint";
        
        // Gán Vị trí (Pose)
        odom.pose.pose.position.x = x_;
        odom.pose.pose.position.y = y_;
        odom.pose.pose.orientation.x = q.x();
        odom.pose.pose.orientation.y = q.y();
        odom.pose.pose.orientation.z = q.z();
        odom.pose.pose.orientation.w = q.w();

        // Gán Vận tốc (Twist) - Cực kỳ quan trọng cho UKF
        odom.twist.twist.linear.x = vx;
        odom.twist.twist.linear.y = 0.0;
        odom.twist.twist.angular.z = vtheta;

        // Ma trận hiệp phương sai cơ bản để báo cho UKF biết mức độ tin cậy
        odom.pose.covariance[0] = 0.01;
        odom.pose.covariance[7] = 0.01;
        odom.pose.covariance[35] = 0.05;
        odom.twist.covariance[0] = 0.01;
        odom.twist.covariance[35] = 0.05;

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