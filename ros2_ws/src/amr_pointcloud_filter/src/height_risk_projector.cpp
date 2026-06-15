#include <rclcpp/rclcpp.hpp>

#include <sensor_msgs/msg/point_cloud2.hpp>
#include <sensor_msgs/point_cloud2_iterator.hpp>
#include <nav_msgs/msg/occupancy_grid.hpp>
#include <geometry_msgs/msg/transform_stamped.hpp>

#include <tf2/LinearMath/Transform.h>
#include <tf2_geometry_msgs/tf2_geometry_msgs.hpp>
#include <tf2_ros/buffer.h>
#include <tf2_ros/transform_listener.h>

#include <algorithm>
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

struct CellKey
{
  int ix;
  int iy;

  bool operator==(const CellKey & other) const
  {
    return ix == other.ix && iy == other.iy;
  }
};

struct CellKeyHash
{
  std::size_t operator()(const CellKey & k) const
  {
    const std::size_t h1 = std::hash<int>()(k.ix * 73856093);
    const std::size_t h2 = std::hash<int>()(k.iy * 19349663);
    return h1 ^ (h2 << 1);
  }
};

struct AccumCell
{
  int count = 0;
  double sum_x = 0.0;
  double sum_y = 0.0;
  double sum_z = 0.0;
  double min_z = std::numeric_limits<double>::infinity();
  double max_z = -std::numeric_limits<double>::infinity();
};

struct MemoryCell
{
  double x = 0.0;
  double y = 0.0;
  double z = 0.0;
  int count = 0;
  rclcpp::Time last_seen;
};

class HeightRiskProjector : public rclcpp::Node
{
public:
  HeightRiskProjector()
  : Node("height_risk_projector"),
    tf_buffer_(this->get_clock()),
    tf_listener_(tf_buffer_)
  {
    input_topic_ = declare_parameter<std::string>("input_topic", "/camera/depth/points_filtered");
    output_cloud_topic_ = declare_parameter<std::string>("output_cloud_topic", "/height_obstacles_cloud");
    clearing_cloud_topic_ = declare_parameter<std::string>("clearing_cloud_topic", "/height_clearing_cloud");
    debug_grid_topic_ = declare_parameter<std::string>("debug_grid_topic", "/height_risk_grid");

    target_frame_ = declare_parameter<std::string>("target_frame", "base_footprint");
    use_latest_tf_ = declare_parameter<bool>("use_latest_tf", true);
    tf_timeout_s_ = declare_parameter<double>("tf_timeout_s", 0.08);

    min_x_ = declare_parameter<double>("min_x", 0.10);
    max_x_ = declare_parameter<double>("max_x", 2.50);
    min_y_ = declare_parameter<double>("min_y", -0.75);
    max_y_ = declare_parameter<double>("max_y", 0.75);
    robot_min_z_ = declare_parameter<double>("robot_min_z", 0.12);
    robot_max_z_ = declare_parameter<double>("robot_max_z", 1.05);

    grid_resolution_ = declare_parameter<double>("grid_resolution", 0.05);
    min_points_per_cell_ = declare_parameter<int>("min_points_per_cell", 2);
    memory_decay_time_s_ = declare_parameter<double>("memory_decay_time", 0.8);
    publish_hz_ = declare_parameter<double>("publish_hz", 5.0);

    publish_clearing_cloud_ = declare_parameter<bool>("publish_clearing_cloud", true);
    clearing_y_step_ = declare_parameter<double>("clearing_y_step", 0.15);
    clearing_z_step_ = declare_parameter<double>("clearing_z_step", 0.20);

    max_input_points_ = declare_parameter<int>("max_input_points", 60000);
    log_debug_ = declare_parameter<bool>("log_debug", true);
    publish_debug_grid_ = declare_parameter<bool>("publish_debug_grid", true);

    if (grid_resolution_ <= 0.0) {
      RCLCPP_WARN(get_logger(), "grid_resolution <= 0. Using 0.05 m");
      grid_resolution_ = 0.05;
    }
    if (min_points_per_cell_ < 1) {
      min_points_per_cell_ = 1;
    }
    if (memory_decay_time_s_ < 0.0) {
      memory_decay_time_s_ = 0.0;
    }

    cloud_pub_ = create_publisher<sensor_msgs::msg::PointCloud2>(
      output_cloud_topic_, rclcpp::SensorDataQoS());

    clearing_pub_ = create_publisher<sensor_msgs::msg::PointCloud2>(
      clearing_cloud_topic_, rclcpp::SensorDataQoS());

    grid_pub_ = create_publisher<nav_msgs::msg::OccupancyGrid>(
      debug_grid_topic_, rclcpp::QoS(rclcpp::KeepLast(1)).reliable().durability_volatile());

    sub_ = create_subscription<sensor_msgs::msg::PointCloud2>(
      input_topic_,
      rclcpp::SensorDataQoS(),
      std::bind(&HeightRiskProjector::cloudCallback, this, std::placeholders::_1));

    RCLCPP_INFO(
      get_logger(),
      "HeightRiskProjector: %s -> %s, target=%s, ROI x[%.2f %.2f] y[%.2f %.2f] z[%.2f %.2f], res=%.2f, min_pts=%d, memory=%.2fs",
      input_topic_.c_str(),
      output_cloud_topic_.c_str(),
      target_frame_.c_str(),
      min_x_, max_x_, min_y_, max_y_, robot_min_z_, robot_max_z_,
      grid_resolution_, min_points_per_cell_, memory_decay_time_s_);
  }

private:
  std::string input_topic_;
  std::string output_cloud_topic_;
  std::string clearing_cloud_topic_;
  std::string debug_grid_topic_;
  std::string target_frame_;

  bool use_latest_tf_;
  double tf_timeout_s_;

  double min_x_;
  double max_x_;
  double min_y_;
  double max_y_;
  double robot_min_z_;
  double robot_max_z_;
  double grid_resolution_;
  int min_points_per_cell_;
  double memory_decay_time_s_;
  double publish_hz_;
  bool publish_clearing_cloud_;
  double clearing_y_step_;
  double clearing_z_step_;
  int max_input_points_;
  bool log_debug_;
  bool publish_debug_grid_;

  bool last_publish_valid_ = false;
  bool last_debug_valid_ = false;
  rclcpp::Time last_publish_time_;
  rclcpp::Time last_debug_time_;

  tf2_ros::Buffer tf_buffer_;
  tf2_ros::TransformListener tf_listener_;

  rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr sub_;
  rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr cloud_pub_;
  rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr clearing_pub_;
  rclcpp::Publisher<nav_msgs::msg::OccupancyGrid>::SharedPtr grid_pub_;

  std::unordered_map<CellKey, MemoryCell, CellKeyHash> memory_;

  bool dueToPublish(const rclcpp::Time & now)
  {
    if (publish_hz_ <= 0.0 || !last_publish_valid_) {
      return true;
    }
    return (now - last_publish_time_).seconds() >= (1.0 / publish_hz_);
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

  float readFloat(const std::vector<uint8_t> & data, const size_t offset)
  {
    float value;
    std::memcpy(&value, &data[offset], sizeof(float));
    return value;
  }

  bool lookupTransform(
    const sensor_msgs::msg::PointCloud2::SharedPtr msg,
    tf2::Transform & tf_out)
  {
    if (msg->header.frame_id.empty()) {
      RCLCPP_WARN_THROTTLE(
        get_logger(), *get_clock(), 2000,
        "Input cloud frame_id is empty, skip frame");
      return false;
    }

    try {
      geometry_msgs::msg::TransformStamped tf_msg;
      if (use_latest_tf_) {
        tf_msg = tf_buffer_.lookupTransform(
          target_frame_,
          msg->header.frame_id,
          tf2::TimePointZero,
          tf2::durationFromSec(tf_timeout_s_));
      } else {
        tf_msg = tf_buffer_.lookupTransform(
          target_frame_,
          msg->header.frame_id,
          msg->header.stamp,
          tf2::durationFromSec(tf_timeout_s_));
      }

      tf2::fromMsg(tf_msg.transform, tf_out);
      return true;
    } catch (const tf2::TransformException & ex) {
      RCLCPP_WARN_THROTTLE(
        get_logger(), *get_clock(), 2000,
        "Cannot transform %s -> %s: %s",
        msg->header.frame_id.c_str(), target_frame_.c_str(), ex.what());
      return false;
    }
  }

  void pruneMemory(const rclcpp::Time & now)
  {
    if (memory_decay_time_s_ <= 0.0) {
      memory_.clear();
      return;
    }

    for (auto it = memory_.begin(); it != memory_.end(); ) {
      const double age = (now - it->second.last_seen).seconds();
      if (age > memory_decay_time_s_) {
        it = memory_.erase(it);
      } else {
        ++it;
      }
    }
  }

  std::vector<PointXYZ> processCloud(
    const sensor_msgs::msg::PointCloud2::SharedPtr msg,
    const tf2::Transform & tf,
    const rclcpp::Time & now,
    size_t & finite_count,
    size_t & roi_count,
    size_t & height_count,
    size_t & accepted_cells)
  {
    finite_count = 0;
    roi_count = 0;
    height_count = 0;
    accepted_cells = 0;

    const int x_off = fieldOffset(*msg, "x");
    const int y_off = fieldOffset(*msg, "y");
    const int z_off = fieldOffset(*msg, "z");

    if (x_off < 0 || y_off < 0 || z_off < 0) {
      RCLCPP_WARN_THROTTLE(
        get_logger(), *get_clock(), 2000,
        "Input PointCloud2 does not contain x/y/z fields");
      return {};
    }

    if (msg->width == 0 || msg->height == 0 || msg->point_step == 0 || msg->row_step == 0) {
      return {};
    }

    std::unordered_map<CellKey, AccumCell, CellKeyHash> frame_cells;
    frame_cells.reserve(static_cast<size_t>(std::max(100u, msg->width * msg->height / 8u)));

    size_t visited = 0;
    const size_t max_points = max_input_points_ > 0 ? static_cast<size_t>(max_input_points_) : std::numeric_limits<size_t>::max();

    for (uint32_t v = 0; v < msg->height; ++v) {
      const size_t row_base = static_cast<size_t>(v) * msg->row_step;

      for (uint32_t u = 0; u < msg->width; ++u) {
        if (visited >= max_points) {
          break;
        }
        visited++;

        const size_t base = row_base + static_cast<size_t>(u) * msg->point_step;
        const size_t need = base + static_cast<size_t>(std::max({x_off, y_off, z_off})) + sizeof(float);
        if (need > msg->data.size()) {
          continue;
        }

        const float sx = readFloat(msg->data, base + x_off);
        const float sy = readFloat(msg->data, base + y_off);
        const float sz = readFloat(msg->data, base + z_off);

        if (!std::isfinite(sx) || !std::isfinite(sy) || !std::isfinite(sz)) {
          continue;
        }
        finite_count++;

        const tf2::Vector3 p_base = tf * tf2::Vector3(sx, sy, sz);
        const double x = p_base.x();
        const double y = p_base.y();
        const double z = p_base.z();

        if (x < min_x_ || x > max_x_ || y < min_y_ || y > max_y_) {
          continue;
        }
        roi_count++;

        if (z < robot_min_z_ || z > robot_max_z_) {
          continue;
        }
        height_count++;

        const CellKey key{
          static_cast<int>(std::floor(x / grid_resolution_)),
          static_cast<int>(std::floor(y / grid_resolution_))
        };

        auto & cell = frame_cells[key];
        cell.count++;
        cell.sum_x += x;
        cell.sum_y += y;
        cell.sum_z += z;
        cell.min_z = std::min(cell.min_z, z);
        cell.max_z = std::max(cell.max_z, z);

        RCLCPP_INFO(
          get_logger(),
          "ROI Z range: min=%.3f max=%.3f",
          min_observed_z,
          max_observed_z);
      }
    }

    for (const auto & item : frame_cells) {
      const auto & cell = item.second;
      if (cell.count < min_points_per_cell_) {
        continue;
      }

      MemoryCell mem;
      mem.x = cell.sum_x / static_cast<double>(cell.count);
      mem.y = cell.sum_y / static_cast<double>(cell.count);
      mem.z = std::clamp(cell.sum_z / static_cast<double>(cell.count), robot_min_z_, robot_max_z_);
      mem.count = cell.count;
      mem.last_seen = now;

      memory_[item.first] = mem;
      accepted_cells++;
    }

    pruneMemory(now);

    std::vector<PointXYZ> output;
    output.reserve(memory_.size());
    for (const auto & item : memory_) {
      const auto & mem = item.second;
      output.push_back(PointXYZ{
        static_cast<float>(mem.x),
        static_cast<float>(mem.y),
        static_cast<float>(mem.z)});
    }

    return output;
  }

  sensor_msgs::msg::PointCloud2 makeCloudMsg(
    const std::vector<PointXYZ> & points,
    const rclcpp::Time & stamp)
  {
    sensor_msgs::msg::PointCloud2 output;
    output.header.stamp = stamp;
    output.header.frame_id = target_frame_;
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

  std::vector<PointXYZ> makeClearingPoints()
  {
    std::vector<PointXYZ> points;
    if (!publish_clearing_cloud_) {
      return points;
    }

    const double y_step = clearing_y_step_ > 0.0 ? clearing_y_step_ : 0.15;
    const double z_step = clearing_z_step_ > 0.0 ? clearing_z_step_ : 0.20;

    // Các endpoint này chỉ dùng cho source clearing=True, marking=False trong VoxelLayer.
    // Mục đích là xóa obstacle cũ trong vùng quan sát của height layer trước khi đánh dấu lại cloud mới.
    for (double y = min_y_; y <= max_y_ + 1e-6; y += y_step) {
      for (double z = robot_min_z_; z <= robot_max_z_ + 1e-6; z += z_step) {
        points.push_back(PointXYZ{
          static_cast<float>(max_x_),
          static_cast<float>(y),
          static_cast<float>(z)});
      }
    }

    return points;
  }

  nav_msgs::msg::OccupancyGrid makeGridMsg(const rclcpp::Time & stamp)
  {
    nav_msgs::msg::OccupancyGrid grid;
    grid.header.stamp = stamp;
    grid.header.frame_id = target_frame_;

    const int width = static_cast<int>(std::ceil((max_x_ - min_x_) / grid_resolution_));
    const int height = static_cast<int>(std::ceil((max_y_ - min_y_) / grid_resolution_));

    grid.info.resolution = static_cast<float>(grid_resolution_);
    grid.info.width = static_cast<uint32_t>(std::max(1, width));
    grid.info.height = static_cast<uint32_t>(std::max(1, height));
    grid.info.origin.position.x = min_x_;
    grid.info.origin.position.y = min_y_;
    grid.info.origin.position.z = 0.0;
    grid.info.origin.orientation.w = 1.0;
    grid.data.assign(static_cast<size_t>(grid.info.width * grid.info.height), 0);

    const auto now = stamp;
    for (const auto & item : memory_) {
      const auto & mem = item.second;
      const int gx = static_cast<int>(std::floor((mem.x - min_x_) / grid_resolution_));
      const int gy = static_cast<int>(std::floor((mem.y - min_y_) / grid_resolution_));
      if (gx < 0 || gy < 0 || gx >= static_cast<int>(grid.info.width) || gy >= static_cast<int>(grid.info.height)) {
        continue;
      }

      double value = 100.0;
      if (memory_decay_time_s_ > 0.0) {
        const double age = std::max(0.0, (now - mem.last_seen).seconds());
        value = 100.0 * std::max(0.0, 1.0 - age / memory_decay_time_s_);
      }

      const size_t index = static_cast<size_t>(gy) * grid.info.width + static_cast<size_t>(gx);
      grid.data[index] = static_cast<int8_t>(std::clamp(value, 1.0, 100.0));
    }

    return grid;
  }

  void logStats(
    const rclcpp::Time & now,
    size_t finite_count,
    size_t roi_count,
    size_t height_count,
    size_t accepted_cells,
    size_t output_points)
  {
    if (!log_debug_) {
      return;
    }
    if (last_debug_valid_ && (now - last_debug_time_).seconds() < 2.0) {
      return;
    }
    last_debug_valid_ = true;
    last_debug_time_ = now;

    RCLCPP_INFO(
      get_logger(),
      "height risk: finite=%zu roi=%zu height=%zu accepted_cells=%zu memory=%zu output=%zu",
      finite_count,
      roi_count,
      height_count,
      accepted_cells,
      memory_.size(),
      output_points);
  }

  void cloudCallback(const sensor_msgs::msg::PointCloud2::SharedPtr msg)
  {
    const auto now = get_clock()->now();
    if (!dueToPublish(now)) {
      return;
    }

    tf2::Transform tf;
    if (!lookupTransform(msg, tf)) {
      return;
    }

    size_t finite_count = 0;
    size_t roi_count = 0;
    size_t height_count = 0;
    size_t accepted_cells = 0;

    const auto points = processCloud(
      msg, tf, now,
      finite_count,
      roi_count,
      height_count,
      accepted_cells);

    auto cloud_msg = makeCloudMsg(points, now);
    cloud_pub_->publish(cloud_msg);

    if (publish_clearing_cloud_) {
      const auto clearing_points = makeClearingPoints();
      auto clearing_msg = makeCloudMsg(clearing_points, now);
      clearing_pub_->publish(clearing_msg);
    }

    if (publish_debug_grid_) {
      auto grid_msg = makeGridMsg(now);
      grid_pub_->publish(grid_msg);
    }

    last_publish_valid_ = true;
    last_publish_time_ = now;

    logStats(now, finite_count, roi_count, height_count, accepted_cells, points.size());
  }
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<HeightRiskProjector>());
  rclcpp::shutdown();
  return 0;
}
