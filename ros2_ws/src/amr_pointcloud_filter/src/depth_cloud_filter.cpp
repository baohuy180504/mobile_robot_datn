#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/point_cloud2.hpp>
#include <sensor_msgs/point_cloud2_iterator.hpp>

#include <cmath>
#include <cstring>
#include <limits>
#include <string>
#include <unordered_map>
#include <vector>

struct PointXYZ
{
  float x;
  float y;
  float z;
};

struct VoxelKey
{
  int ix;
  int iy;
  int iz;

  bool operator==(const VoxelKey & other) const
  {
    return ix == other.ix && iy == other.iy && iz == other.iz;
  }
};

struct VoxelKeyHash
{
  std::size_t operator()(const VoxelKey & k) const
  {
    std::size_t h1 = std::hash<int>()(k.ix * 73856093);
    std::size_t h2 = std::hash<int>()(k.iy * 19349663);
    std::size_t h3 = std::hash<int>()(k.iz * 83492791);
    return h1 ^ (h2 << 1) ^ (h3 << 2);
  }
};

class DepthCloudFilter : public rclcpp::Node
{
public:
  DepthCloudFilter() : Node("depth_cloud_filter")
  {
    input_topic_ = declare_parameter<std::string>("input_topic", "/camera/depth/points");
    nav_output_topic_ = declare_parameter<std::string>("nav_output_topic", "/camera/depth/points_filtered");
    octomap_output_topic_ = declare_parameter<std::string>("octomap_output_topic", "/octomap_cloud");

    nav_publish_hz_ = declare_parameter<double>("nav_publish_hz", 3.0);
    octomap_publish_hz_ = declare_parameter<double>("octomap_publish_hz", 0.5);

    nav_leaf_size_ = declare_parameter<double>("nav_leaf_size", 0.08);
    octomap_leaf_size_ = declare_parameter<double>("octomap_leaf_size", 0.12);

    nav_pixel_step_ = declare_parameter<int>("nav_pixel_step", 4);
    octomap_pixel_step_ = declare_parameter<int>("octomap_pixel_step", 6);

    min_depth_ = declare_parameter<double>("min_depth", 0.30);
    max_depth_ = declare_parameter<double>("max_depth", 3.00);

    min_x_ = declare_parameter<double>("min_x", -2.00);
    max_x_ = declare_parameter<double>("max_x", 2.00);
    min_y_ = declare_parameter<double>("min_y", -1.50);
    max_y_ = declare_parameter<double>("max_y", 1.50);

    restamp_ = declare_parameter<bool>("restamp", true);
    output_frame_id_ = declare_parameter<std::string>("output_frame_id", "");

    log_debug_ = declare_parameter<bool>("log_debug", true);

    //auto input_qos = rclcpp::SensorDataQoS();
    auto input_qos = rclcpp::QoS(rclcpp::KeepLast(10))
        .reliable()
        .durability_volatile();
    auto output_qos = rclcpp::SensorDataQoS();
    nav_pub_ = create_publisher<sensor_msgs::msg::PointCloud2>(nav_output_topic_, output_qos);
    octomap_pub_ = create_publisher<sensor_msgs::msg::PointCloud2>(octomap_output_topic_, output_qos);

    sub_ = create_subscription<sensor_msgs::msg::PointCloud2>(
      input_topic_,
      input_qos,
      std::bind(&DepthCloudFilter::cloudCallback, this, std::placeholders::_1)
    );

    RCLCPP_INFO(
      get_logger(),
      "FAST DepthCloudFilter: %s -> nav:%s %.2fHz leaf=%.3f step=%d, octomap:%s %.2fHz leaf=%.3f step=%d",
      input_topic_.c_str(),
      nav_output_topic_.c_str(),
      nav_publish_hz_,
      nav_leaf_size_,
      nav_pixel_step_,
      octomap_output_topic_.c_str(),
      octomap_publish_hz_,
      octomap_leaf_size_,
      octomap_pixel_step_
    );
  }

private:
  std::string input_topic_;
  std::string nav_output_topic_;
  std::string octomap_output_topic_;
  std::string output_frame_id_;

  double nav_publish_hz_;
  double octomap_publish_hz_;
  double nav_leaf_size_;
  double octomap_leaf_size_;

  int nav_pixel_step_;
  int octomap_pixel_step_;

  double min_depth_;
  double max_depth_;
  double min_x_;
  double max_x_;
  double min_y_;
  double max_y_;

  bool restamp_;
  bool log_debug_;

  bool last_nav_valid_ = false;
  bool last_octomap_valid_ = false;
  bool last_debug_valid_ = false;

  rclcpp::Time last_nav_pub_;
  rclcpp::Time last_octomap_pub_;
  rclcpp::Time last_debug_log_;

  rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr sub_;
  rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr nav_pub_;
  rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr octomap_pub_;

  bool dueToPublish(const rclcpp::Time & now, const rclcpp::Time & last_time, bool valid, double hz)
  {
    if (hz <= 0.0) {
      return true;
    }

    if (!valid) {
      return true;
    }

    return (now - last_time).seconds() >= (1.0 / hz);
  }

  int fieldOffset(const sensor_msgs::msg::PointCloud2 & msg, const std::string & name)
  {
    for (const auto & field : msg.fields) {
      if (field.name == name) {
        return static_cast<int>(field.offset);
      }
    }
    return -1;
  }

  float readFloat(const std::vector<uint8_t> & data, size_t offset)
  {
    float value;
    std::memcpy(&value, &data[offset], sizeof(float));
    return value;
  }

  std::vector<PointXYZ> filterManual(
    const sensor_msgs::msg::PointCloud2::SharedPtr msg,
    double leaf_size,
    int pixel_step,
    size_t & sampled_count,
    size_t & finite_count,
    size_t & cropped_count)
  {
    sampled_count = 0;
    finite_count = 0;
    cropped_count = 0;

    std::vector<PointXYZ> output;

    const int x_off = fieldOffset(*msg, "x");
    const int y_off = fieldOffset(*msg, "y");
    const int z_off = fieldOffset(*msg, "z");

    if (x_off < 0 || y_off < 0 || z_off < 0) {
      RCLCPP_WARN_THROTTLE(
        get_logger(),
        *get_clock(),
        2000,
        "Input PointCloud2 does not contain x/y/z fields"
      );
      return output;
    }

    if (pixel_step < 1) {
      pixel_step = 1;
    }

    const uint32_t height = msg->height > 0 ? msg->height : 1;
    const uint32_t width = msg->width;

    if (height == 0 || width == 0 || msg->point_step == 0 || msg->row_step == 0) {
      return output;
    }

    std::unordered_map<VoxelKey, PointXYZ, VoxelKeyHash> voxels;
    voxels.reserve((width * height) / (pixel_step * pixel_step) + 100);

    const double inv_leaf = leaf_size > 0.0 ? 1.0 / leaf_size : 0.0;

    for (uint32_t v = 0; v < height; v += static_cast<uint32_t>(pixel_step)) {
      const size_t row_base = static_cast<size_t>(v) * msg->row_step;

      for (uint32_t u = 0; u < width; u += static_cast<uint32_t>(pixel_step)) {
        const size_t base = row_base + static_cast<size_t>(u) * msg->point_step;

        const size_t need = base + std::max({x_off, y_off, z_off}) + sizeof(float);
        if (need > msg->data.size()) {
          continue;
        }

        sampled_count++;

        const float x = readFloat(msg->data, base + x_off);
        const float y = readFloat(msg->data, base + y_off);
        const float z = readFloat(msg->data, base + z_off);

        if (!std::isfinite(x) || !std::isfinite(y) || !std::isfinite(z)) {
          continue;
        }

        finite_count++;

        // camera_depth_optical_frame: x ngang ảnh, y dọc ảnh, z chiều sâu phía trước camera.
        if (z < min_depth_ || z > max_depth_) {
          continue;
        }

        if (x < min_x_ || x > max_x_) {
          continue;
        }

        if (y < min_y_ || y > max_y_) {
          continue;
        }

        cropped_count++;

        PointXYZ p{x, y, z};

        if (leaf_size <= 0.0) {
          output.push_back(p);
          continue;
        }

        VoxelKey key{
          static_cast<int>(std::floor(x * inv_leaf)),
          static_cast<int>(std::floor(y * inv_leaf)),
          static_cast<int>(std::floor(z * inv_leaf))
        };

        if (voxels.find(key) == voxels.end()) {
          voxels.emplace(key, p);
        }
      }
    }

    if (leaf_size > 0.0) {
      output.reserve(voxels.size());
      for (const auto & item : voxels) {
        output.push_back(item.second);
      }
    }

    return output;
  }

  sensor_msgs::msg::PointCloud2 makeCloudMsg(
    const std::vector<PointXYZ> & points,
    const sensor_msgs::msg::PointCloud2::SharedPtr input_msg,
    const rclcpp::Time & now)
  {
    sensor_msgs::msg::PointCloud2 output;

    output.header = input_msg->header;

    if (!output_frame_id_.empty()) {
      output.header.frame_id = output_frame_id_;
    }

    if (restamp_) {
      output.header.stamp = now;
    }

    output.height = 1;
    output.width = static_cast<uint32_t>(points.size());
    output.is_bigendian = false;
    output.is_dense = true;

    sensor_msgs::PointCloud2Modifier modifier(output);
    modifier.setPointCloud2FieldsByString(1, "xyz");
    modifier.resize(points.size());

    sensor_msgs::PointCloud2Iterator<float> iter_x(output, "x");
    sensor_msgs::PointCloud2Iterator<float> iter_y(output, "y");
    sensor_msgs::PointCloud2Iterator<float> iter_z(output, "z");

    for (const auto & p : points) {
      *iter_x = p.x;
      *iter_y = p.y;
      *iter_z = p.z;
      ++iter_x;
      ++iter_y;
      ++iter_z;
    }

    return output;
  }

  void logStats(
    const rclcpp::Time & now,
    const char * name,
    size_t sampled,
    size_t finite,
    size_t cropped,
    size_t out)
  {
    if (!log_debug_) {
      return;
    }

    if (last_debug_valid_ && (now - last_debug_log_).seconds() < 2.0) {
      return;
    }

    last_debug_log_ = now;
    last_debug_valid_ = true;

    RCLCPP_INFO(
      get_logger(),
      "%s stats: sampled=%zu finite=%zu cropped=%zu out=%zu crop[x %.2f..%.2f, y %.2f..%.2f, z %.2f..%.2f]",
      name,
      sampled,
      finite,
      cropped,
      out,
      min_x_,
      max_x_,
      min_y_,
      max_y_,
      min_depth_,
      max_depth_
    );
  }

  void cloudCallback(const sensor_msgs::msg::PointCloud2::SharedPtr msg)
  {
    const auto now = get_clock()->now();

    const bool nav_due = dueToPublish(now, last_nav_pub_, last_nav_valid_, nav_publish_hz_);
    const bool octomap_due = dueToPublish(now, last_octomap_pub_, last_octomap_valid_, octomap_publish_hz_);

    if (!nav_due && !octomap_due) {
      return;
    }

    if (nav_due) {
      size_t sampled = 0;
      size_t finite = 0;
      size_t cropped = 0;

      const auto points = filterManual(
        msg,
        nav_leaf_size_,
        nav_pixel_step_,
        sampled,
        finite,
        cropped
      );

      logStats(now, "nav", sampled, finite, cropped, points.size());

      if (!points.empty()) {
        auto out_msg = makeCloudMsg(points, msg, now);
        nav_pub_->publish(out_msg);
        last_nav_pub_ = now;
        last_nav_valid_ = true;
      }
    }

    if (octomap_due) {
      size_t sampled = 0;
      size_t finite = 0;
      size_t cropped = 0;

      const auto points = filterManual(
        msg,
        octomap_leaf_size_,
        octomap_pixel_step_,
        sampled,
        finite,
        cropped
      );

      logStats(now, "octomap", sampled, finite, cropped, points.size());

      if (!points.empty()) {
        auto out_msg = makeCloudMsg(points, msg, now);
        octomap_pub_->publish(out_msg);
        last_octomap_pub_ = now;
        last_octomap_valid_ = true;
      }
    }
  }
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<DepthCloudFilter>());
  rclcpp::shutdown();
  return 0;
}