#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/twist.hpp>
#include <nav_msgs/msg/odometry.hpp>
#include <tf2_ros/transform_broadcaster.h>
#include <tf2/LinearMath/Quaternion.h>
#include <geometry_msgs/msg/transform_stamped.hpp>

#include <fcntl.h>
#include <termios.h>
#include <unistd.h>
#include <string>
#include <cmath>

class ArduinoBridge : public rclcpp::Node
{
public:
    ArduinoBridge() : Node("arduino_bridge"), x_(0.0), y_(0.0), theta_(0.0), first_read_(true), initial_yaw_(0.0) // KHỞI TẠO BIẾN
    {
        odom_pub_ = this->create_publisher<nav_msgs::msg::Odometry>("odom", 10);
        tf_broadcaster_ = std::make_unique<tf2_ros::TransformBroadcaster>(*this);

        cmd_vel_sub_ = this->create_subscription<geometry_msgs::msg::Twist>(
            "cmd_vel", 10, std::bind(&ArduinoBridge::cmd_vel_callback, this, std::placeholders::_1));

        // Mở cổng Serial kết nối Arduino Mega
        open_serial_port("/dev/arduino_mega", B115200);

        timer_ = this->create_wall_timer(
            std::chrono::milliseconds(33), // Tần số 30Hz
            std::bind(&ArduinoBridge::read_serial_and_publish_odom, this));

        RCLCPP_INFO(this->get_logger(), "🚀 Cầu nối C++ Arduino Bridge đã sẵn sàng!");
    }

    ~ArduinoBridge()
    {
        if (serial_fd_ != -1) close(serial_fd_);
    }

private:
    int serial_fd_;
    std::string serial_buffer_ = "";
    
    // Hệ số toán học quy đổi Encoder
    const double D_P = 0.000055185; // Khoảng cách 1 xung (mét)
    const double PI = 3.14159265359;

    // Tọa độ và trạng thái hiện tại
    double x_, y_, theta_;
    long last_pos_left_ = 0;
    long last_pos_right_ = 0;
    bool first_read_;
    double initial_yaw_; // KHAI BÁO BIẾN LƯU GÓC BAN ĐẦU

    rclcpp::Publisher<nav_msgs::msg::Odometry>::SharedPtr odom_pub_;
    rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr cmd_vel_sub_;
    std::unique_ptr<tf2_ros::TransformBroadcaster> tf_broadcaster_;
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
            serial_buffer_ += buf; // Cộng dồn vào bộ đệm để chống đứt gãy chuỗi

            size_t pos;
            // Xử lý từng dòng lệnh có kết thúc bằng '\n'
            while ((pos = serial_buffer_.find('\n')) != std::string::npos) {
                std::string line = serial_buffer_.substr(0, pos);
                serial_buffer_.erase(0, pos + 1);
                process_sensor_data(line);
            }
        }
    }

    void process_sensor_data(const std::string& data)
    {
        // Kiểm tra đúng định dạng bắt đầu bằng "e:"
        if (data.rfind("e:", 0) == 0) {
            std::string payload = data.substr(2); // Cắt bỏ "e:"
            size_t comma1 = payload.find(',');
            size_t comma2 = payload.find(',', comma1 + 1);

            if (comma1 != std::string::npos && comma2 != std::string::npos) {
                try {
                    // 1. Tách biến
                    long pos_left = std::stol(payload.substr(0, comma1));
                    long pos_right = std::stol(payload.substr(comma1 + 1, comma2 - comma1 - 1));
                    float yaw_deg = std::stof(payload.substr(comma2 + 1));

                    double yaw_rad = yaw_deg * PI / 180.0; // Đổi ra Radian ngay lập tức

                    // Tránh xe bị "nhảy cóc" hàng chục mét ở giây đầu tiên và thiết lập mốc 0 độ
                    if (first_read_) {
                        last_pos_left_ = pos_left;
                        last_pos_right_ = pos_right;
                        initial_yaw_ = yaw_rad; // BẮT BUỘC: Khóa góc la bàn đầu tiên làm mốc 0
                        first_read_ = false;
                    }

                    // 2. Tính Delta Xung
                    long delta_l = pos_left - last_pos_left_;
                    long delta_r = pos_right - last_pos_right_;
                    last_pos_left_ = pos_left;
                    last_pos_right_ = pos_right;

                    // 3. Quy đổi ra mét
                    double d_l = delta_l * D_P;
                    double d_r = delta_r * D_P;
                    double d_center = (d_l + d_r) / 2.0;

                    // 4. Xử lý góc Yaw (Trừ đi mốc ban đầu)
                    double current_yaw = yaw_rad - initial_yaw_;

                    // NẾU TIA LASER VẪN XOAY THEO XE, BỎ DẤU "//" Ở DÒNG DƯỚI ĐỂ ĐẢO CHIỀU:
                    //current_yaw = -current_yaw; 

                    // Chuẩn hóa góc về mốc [-PI, PI] của ROS 2
                    while (current_yaw > PI) current_yaw -= 2.0 * PI;
                    while (current_yaw < -PI) current_yaw += 2.0 * PI;

                    // 5. Tính Tọa độ X, Y tuyệt đối
                    x_ += d_center * cos(current_yaw);
                    y_ += d_center * sin(current_yaw);
                    theta_ = current_yaw; 

                    // 6. Đẩy dữ liệu lên mạng lưới ROS
                    publish_tf_and_odom();
                } catch (const std::exception& e) {
                    RCLCPP_WARN(this->get_logger(), "Nhiễu Serial, bỏ qua gói tin lỗi...");
                }
            }
        }
    }

    void publish_tf_and_odom()
    {
        rclcpp::Time now = this->get_clock()->now();

        tf2::Quaternion q;
        q.setRPY(0, 0, theta_);

        // Bắn TF (Khung xương)
        geometry_msgs::msg::TransformStamped t;
        t.header.stamp = now;
        t.header.frame_id = "odom";
        t.child_frame_id = "base_footprint";
        t.transform.translation.x = x_;
        t.transform.translation.y = y_;
        t.transform.translation.z = 0.0;
        t.transform.rotation.x = q.x();
        t.transform.rotation.y = q.y();
        t.transform.rotation.z = q.z();
        t.transform.rotation.w = q.w();
        tf_broadcaster_->sendTransform(t);

        // Bắn Odom Topic (Cho Nav2)
        nav_msgs::msg::Odometry odom;
        odom.header.stamp = now;
        odom.header.frame_id = "odom";
        odom.child_frame_id = "base_footprint";
        odom.pose.pose.position.x = x_;
        odom.pose.pose.position.y = y_;
        odom.pose.pose.orientation = t.transform.rotation;
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