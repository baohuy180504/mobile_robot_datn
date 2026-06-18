#include <rclcpp/rclcpp.hpp>

#include <sensor_msgs/msg/point_cloud2.hpp>
#include <sensor_msgs/point_cloud2_iterator.hpp>
#include <nav_msgs/msg/occupancy_grid.hpp>
#include <geometry_msgs/msg/transform_stamped.hpp>

#include <tf2/LinearMath/Transform.h>
#include <tf2/utils.h>
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

// ============================================================================
// GHRF — Gaussian Height Risk Field
//
// Thay cho ngưỡng chiều cao nhị phân (z trong [robot_min_z, robot_max_z] -> mark,
// ngoài -> bỏ), mỗi điểm được gán trọng số Gaussian theo độ lệch so với tâm vùng
// nguy cơ, với sigma TĂNG THEO KHOẢNG CÁCH tới camera (vì nhiễu structured-light
// của Astra Mini S tăng theo khoảng cách, không cố định như ToF/stereo tốt).
// Mỗi cell sau đó được chuẩn hoá mật độ bằng tanh(count / density_ref_count) để
// nhiễu thưa (1-2 điểm lạc) không đủ tạo obstacle giả, còn vật thật (nhiều điểm)
// vẫn đạt risk cao. Theo thời gian, risk suy giảm exponential thay vì cắt cứng.
// ============================================================================

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
  double sum_gaussian = 0.0;  // tổng trọng số Gaussian theo chiều cao của các điểm trong cell, frame hiện tại
};

struct MemoryCell
{
  double x = 0.0;
  double y = 0.0;
  double z = 0.0;
  int count = 0;
  double risk = 0.0;  // risk [0,1] tại thời điểm quan sát gần nhất, CHƯA suy giảm theo thời gian
  rclcpp::Time last_seen;
};

// Điểm risk dùng chung cho cả cloud visualize (XYZI) và occupancy grid,
// đã áp dụng exponential decay theo tuổi tại thời điểm publish.
struct RiskPoint
{
  float x;
  float y;
  float z;
  float risk;  // [0,1], đã decay
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
    risk_grid_topic_ = declare_parameter<std::string>("risk_grid_topic", "/ghrf_risk_grid");

    target_frame_ = declare_parameter<std::string>("target_frame", "base_footprint");
    use_latest_tf_ = declare_parameter<bool>("use_latest_tf", true);
    tf_timeout_s_ = declare_parameter<double>("tf_timeout_s", 0.08);

    min_x_ = declare_parameter<double>("min_x", 0.10);
    max_x_ = declare_parameter<double>("max_x", 2.50);
    min_y_ = declare_parameter<double>("min_y", -0.75);
    max_y_ = declare_parameter<double>("max_y", 0.75);
    robot_min_z_ = declare_parameter<double>("robot_min_z", 0.12);
    robot_max_z_ = declare_parameter<double>("robot_max_z", 1.05);

    // === GHRF: tham số Gaussian + mật độ + frame camera/publish ===
    sigma_base_ = declare_parameter<double>("sigma_base", 0.05);
    sigma_depth_k_ = declare_parameter<double>("sigma_depth_k", 0.03);
    gaussian_cutoff_sigma_ = declare_parameter<double>("gaussian_cutoff_sigma", 3.5);
    density_ref_count_ = declare_parameter<double>("density_ref_count", 3.0);
    camera_frame_id_ = declare_parameter<std::string>("camera_frame_id", "camera_depth_optical_frame");
    grid_publish_frame_ = declare_parameter<std::string>("grid_publish_frame", "odom");
    risk_prune_epsilon_ = declare_parameter<double>("risk_prune_epsilon", 0.05);

    grid_resolution_ = declare_parameter<double>("grid_resolution", 0.05);
    min_points_per_cell_ = declare_parameter<int>("min_points_per_cell", 2);
    memory_decay_time_s_ = declare_parameter<double>("memory_decay_time", 0.8);
    publish_hz_ = declare_parameter<double>("publish_hz", 5.0);

    max_input_points_ = declare_parameter<int>("max_input_points", 60000);
    log_debug_ = declare_parameter<bool>("log_debug", true);
    publish_risk_grid_ = declare_parameter<bool>("publish_risk_grid", true);

    if (grid_resolution_ <= 0.0) {
      RCLCPP_WARN(get_logger(), "grid_resolution <= 0. Dùng 0.05 m");
      grid_resolution_ = 0.05;
    }
    if (min_points_per_cell_ < 1) {
      min_points_per_cell_ = 1;
    }
    if (memory_decay_time_s_ < 0.0) {
      memory_decay_time_s_ = 0.0;
    }
    if (sigma_base_ <= 0.0) {
      RCLCPP_WARN(get_logger(), "sigma_base <= 0. Dùng 0.05");
      sigma_base_ = 0.05;
    }
    if (sigma_depth_k_ < 0.0) {
      sigma_depth_k_ = 0.0;
    }
    if (gaussian_cutoff_sigma_ <= 0.0) {
      RCLCPP_WARN(get_logger(), "gaussian_cutoff_sigma <= 0. Dùng 3.5");
      gaussian_cutoff_sigma_ = 3.5;
    }
    if (density_ref_count_ <= 0.0) {
      RCLCPP_WARN(get_logger(), "density_ref_count <= 0. Dùng 3.0");
      density_ref_count_ = 3.0;
    }
    if (risk_prune_epsilon_ < 0.0) {
      risk_prune_epsilon_ = 0.0;
    }

    cloud_pub_ = create_publisher<sensor_msgs::msg::PointCloud2>(
      output_cloud_topic_, rclcpp::SensorDataQoS());

    grid_pub_ = create_publisher<nav_msgs::msg::OccupancyGrid>(
      risk_grid_topic_, rclcpp::QoS(rclcpp::KeepLast(1)).reliable().durability_volatile());

    sub_ = create_subscription<sensor_msgs::msg::PointCloud2>(
      input_topic_,
      rclcpp::SensorDataQoS(),
      std::bind(&HeightRiskProjector::cloudCallback, this, std::placeholders::_1));

    RCLCPP_INFO(
      get_logger(),
      "GHRF HeightRiskProjector: %s -> cloud:%s grid:%s(frame=%s), target=%s, "
      "ROI x[%.2f %.2f] y[%.2f %.2f] z[%.2f %.2f], sigma0=%.3f k_sigma=%.3f cutoff=%.1fsigma "
      "density_ref=%.1f, res=%.2f, min_pts=%d, memory=%.2fs",
      input_topic_.c_str(),
      output_cloud_topic_.c_str(),
      risk_grid_topic_.c_str(),
      grid_publish_frame_.c_str(),
      target_frame_.c_str(),
      min_x_, max_x_, min_y_, max_y_, robot_min_z_, robot_max_z_,
      sigma_base_, sigma_depth_k_, gaussian_cutoff_sigma_, density_ref_count_,
      grid_resolution_, min_points_per_cell_, memory_decay_time_s_);
  }

private:
  std::string input_topic_;
  std::string output_cloud_topic_;
  std::string risk_grid_topic_;
  std::string target_frame_;

  bool use_latest_tf_;
  double tf_timeout_s_;

  double min_x_;
  double max_x_;
  double min_y_;
  double max_y_;
  double robot_min_z_;
  double robot_max_z_;

  double sigma_base_;
  double sigma_depth_k_;
  double gaussian_cutoff_sigma_;
  double density_ref_count_;
  std::string camera_frame_id_;
  std::string grid_publish_frame_;
  double risk_prune_epsilon_;

  double grid_resolution_;
  int min_points_per_cell_;
  double memory_decay_time_s_;
  double publish_hz_;

  int max_input_points_;
  bool log_debug_;
  bool publish_risk_grid_;

  bool last_publish_valid_ = false;
  bool last_debug_valid_ = false;
  rclcpp::Time last_publish_time_;
  rclcpp::Time last_debug_time_;

  tf2_ros::Buffer tf_buffer_;
  tf2_ros::TransformListener tf_listener_;

  rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr sub_;
  rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr cloud_pub_;
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

  // Tìm vị trí gốc camera (camera_frame_id_) biểu diễn trong frame của cloud đầu vào.
  // Chỉ lookup 1 lần/frame (không phải 1 lần/điểm) vì TF không đổi trong cả khung hình.
  // Nếu lookup thất bại, trả về false -> processCloud() sẽ dùng sigma_base_ cố định,
  // KHÔNG drop cả frame (fail-safe, đúng tinh thần toàn bộ pipeline này).
  bool lookupCameraOrigin(
    const sensor_msgs::msg::PointCloud2::SharedPtr msg,
    tf2::Vector3 & origin_out)
  {
    if (msg->header.frame_id.empty()) {
      return false;
    }

    try {
      geometry_msgs::msg::TransformStamped tf_msg;
      if (use_latest_tf_) {
        tf_msg = tf_buffer_.lookupTransform(
          msg->header.frame_id,
          camera_frame_id_,
          tf2::TimePointZero,
          tf2::durationFromSec(tf_timeout_s_));
      } else {
        tf_msg = tf_buffer_.lookupTransform(
          msg->header.frame_id,
          camera_frame_id_,
          msg->header.stamp,
          tf2::durationFromSec(tf_timeout_s_));
      }

      origin_out = tf2::Vector3(
        tf_msg.transform.translation.x,
        tf_msg.transform.translation.y,
        tf_msg.transform.translation.z);
      return true;
    } catch (const tf2::TransformException & ex) {
      RCLCPP_WARN_THROTTLE(
        get_logger(), *get_clock(), 2000,
        "Không tìm được camera origin %s -> %s: %s. Dùng sigma_base cố định cho frame này.",
        camera_frame_id_.c_str(), msg->header.frame_id.c_str(), ex.what());
      return false;
    }
  }

  // Risk hiệu dụng tại thời điểm "now": suy giảm exponential theo tuổi quan sát,
  // thay cho kiểu cắt tuyến tính/cứng (linear/hard-cutoff) trước đây.
  double effectiveRisk(const MemoryCell & mem, const rclcpp::Time & now)
  {
    if (memory_decay_time_s_ <= 0.0) {
      return mem.risk;
    }
    const double age = std::max(0.0, (now - mem.last_seen).seconds());
    return mem.risk * std::exp(-age / memory_decay_time_s_);
  }

  void pruneMemory(const rclcpp::Time & now)
  {
    if (memory_decay_time_s_ <= 0.0) {
      memory_.clear();
      return;
    }

    for (auto it = memory_.begin(); it != memory_.end(); ) {
      if (effectiveRisk(it->second, now) < risk_prune_epsilon_) {
        it = memory_.erase(it);
      } else {
        ++it;
      }
    }
  }

  // Tích lũy điểm theo cell, tính trọng số Gaussian theo chiều cao (sigma thích nghi theo
  // khoảng cách), rồi gộp thành risk [0,1] per-cell và ghi vào memory_. KHÔNG còn trả về
  // điểm trực tiếp — danh sách điểm "đang active" được lấy riêng từ memory_ sau khi đã
  // pruneMemory(), qua collectActiveRiskPoints().
  void processCloud(
    const sensor_msgs::msg::PointCloud2::SharedPtr msg,
    const tf2::Transform & tf,
    const rclcpp::Time & now,
    size_t & finite_count,
    size_t & roi_count,
    size_t & gaussian_count,
    size_t & accepted_cells)
  {
    finite_count = 0;
    roi_count = 0;
    gaussian_count = 0;
    accepted_cells = 0;

    const int x_off = fieldOffset(*msg, "x");
    const int y_off = fieldOffset(*msg, "y");
    const int z_off = fieldOffset(*msg, "z");

    if (x_off < 0 || y_off < 0 || z_off < 0) {
      RCLCPP_WARN_THROTTLE(
        get_logger(), *get_clock(), 2000,
        "Input PointCloud2 does not contain x/y/z fields");
      return;
    }

    if (msg->width == 0 || msg->height == 0 || msg->point_step == 0 || msg->row_step == 0) {
      return;
    }

    tf2::Vector3 camera_origin(0.0, 0.0, 0.0);
    const bool camera_origin_valid = lookupCameraOrigin(msg, camera_origin);

    const double z_center = (robot_min_z_ + robot_max_z_) / 2.0;

    std::unordered_map<CellKey, AccumCell, CellKeyHash> frame_cells;
    frame_cells.reserve(static_cast<size_t>(std::max(100u, msg->width * msg->height / 8u)));

    size_t visited = 0;
    const size_t max_points = max_input_points_ > 0 ?
      static_cast<size_t>(max_input_points_) : std::numeric_limits<size_t>::max();

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

        // === GHRF: thay ngưỡng cứng z bằng trọng số Gaussian, sigma thích nghi theo khoảng cách ===
        // depth_m = khoảng cách thật từ tâm camera tới điểm (không phải chỉ z trong optical frame),
        // để đúng cả khi camera_frame_id_ không trùng hệ quy chiếu gốc của cloud.
        double sigma = sigma_base_;
        if (camera_origin_valid) {
          const tf2::Vector3 p_cam(sx, sy, sz);
          const double depth_m = (p_cam - camera_origin).length();
          sigma = sigma_base_ + sigma_depth_k_ * depth_m;
        }
        if (sigma < 1e-4) {
          sigma = 1e-4;
        }

        const double dz = z - z_center;
        if (std::fabs(dz) > gaussian_cutoff_sigma_ * sigma) {
          // Lệch quá xa tâm vùng nguy cơ theo sigma hiện tại -> trọng số ~0, bỏ qua để tiết kiệm compute.
          continue;
        }
        gaussian_count++;

        const double gaussian_w = std::exp(-(dz * dz) / (2.0 * sigma * sigma));

        const CellKey key{
          static_cast<int>(std::floor(x / grid_resolution_)),
          static_cast<int>(std::floor(y / grid_resolution_))
        };

        auto & cell = frame_cells[key];
        cell.count++;
        cell.sum_x += x;
        cell.sum_y += y;
        cell.sum_z += z;
        cell.sum_gaussian += gaussian_w;
      }
    }

    for (const auto & item : frame_cells) {
      const auto & cell = item.second;
      if (cell.count < min_points_per_cell_) {
        continue;
      }

      // avg_gaussian: trọng số Gaussian trung bình của cell (~1 nếu hầu hết điểm gần z_center).
      // density_factor: tanh(count/N_ref) — kích hoạt mềm theo mật độ, nhiễu thưa (count nhỏ) bị dập,
      // vật thật (count cao) gần như không bị giảm (tanh tiến tới 1).
      const double avg_gaussian = cell.sum_gaussian / static_cast<double>(cell.count);
      const double density_factor = std::tanh(static_cast<double>(cell.count) / density_ref_count_);
      const double risk = std::clamp(avg_gaussian * density_factor, 0.0, 1.0);

      MemoryCell mem;
      mem.x = cell.sum_x / static_cast<double>(cell.count);
      mem.y = cell.sum_y / static_cast<double>(cell.count);
      mem.z = std::clamp(cell.sum_z / static_cast<double>(cell.count), robot_min_z_, robot_max_z_);
      mem.count = cell.count;
      mem.risk = risk;
      mem.last_seen = now;

      memory_[item.first] = mem;
      accepted_cells++;
    }
  }

  // Lấy danh sách điểm đang "active" (risk hiệu dụng >= risk_prune_epsilon_) từ memory_,
  // dùng chung cho cả cloud visualize và occupancy grid để 2 output luôn nhất quán.
  std::vector<RiskPoint> collectActiveRiskPoints(const rclcpp::Time & now)
  {
    std::vector<RiskPoint> points;
    points.reserve(memory_.size());

    for (const auto & item : memory_) {
      const auto & mem = item.second;
      const double risk = effectiveRisk(mem, now);
      if (risk < risk_prune_epsilon_) {
        continue;
      }

      points.push_back(RiskPoint{
        static_cast<float>(mem.x),
        static_cast<float>(mem.y),
        static_cast<float>(mem.z),
        static_cast<float>(risk)});
    }

    return points;
  }

  // Cloud XYZI chỉ phục vụ RViz/debug/hình minh hoạ cho paper — intensity mang giá trị risk*100
  // để dễ so sánh trực quan với occupancy grid. KHÔNG còn publisher nào trong Nav2 đọc cloud này.
  sensor_msgs::msg::PointCloud2 makeCloudMsg(
    const std::vector<RiskPoint> & points,
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
    modifier.setPointCloud2FieldsByString(2, "xyz", "intensity");
    modifier.resize(points.size());

    sensor_msgs::PointCloud2Iterator<float> iter_x(output, "x");
    sensor_msgs::PointCloud2Iterator<float> iter_y(output, "y");
    sensor_msgs::PointCloud2Iterator<float> iter_z(output, "z");
    sensor_msgs::PointCloud2Iterator<float> iter_i(output, "intensity");

    for (const auto & p : points) {
      *iter_x = p.x;
      *iter_y = p.y;
      *iter_z = p.z;
      *iter_i = p.risk * 100.0f;
      ++iter_x;
      ++iter_y;
      ++iter_z;
      ++iter_i;
    }

    return output;
  }

  // Dựng OccupancyGrid risk [0,100] trong ROI cục bộ (target_frame_, vd base_footprint),
  // sau đó "gắn lại" (relabel) sang grid_publish_frame_ (vd odom) bằng MỘT lần TF lookup duy nhất.
  // Mẹo: nav_msgs/OccupancyGrid.info.origin cho phép xoay tuỳ ý, không chỉ tịnh tiến — nên chỉ cần
  // biến đổi origin (tịnh tiến + yaw, lấy qua tf2::getYaw) một lần, dữ liệu từng cell giữ nguyên.
  // Nhờ vậy, costmap layer phía sau đọc grid này KHÔNG cần thêm bất kỳ TF lookup nào nữa.
  nav_msgs::msg::OccupancyGrid makeRiskGridMsg(
    const std::vector<RiskPoint> & points,
    const rclcpp::Time & stamp)
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
    grid.data.assign(
      static_cast<size_t>(grid.info.width) * static_cast<size_t>(grid.info.height), 0);

    for (const auto & p : points) {
      const int gx = static_cast<int>(std::floor((p.x - min_x_) / grid_resolution_));
      const int gy = static_cast<int>(std::floor((p.y - min_y_) / grid_resolution_));
      if (gx < 0 || gy < 0 ||
        gx >= static_cast<int>(grid.info.width) || gy >= static_cast<int>(grid.info.height))
      {
        continue;
      }

      const size_t index = static_cast<size_t>(gy) * grid.info.width + static_cast<size_t>(gx);
      grid.data[index] = static_cast<int8_t>(std::clamp(p.risk * 100.0f, 1.0f, 100.0f));
    }

    geometry_msgs::msg::TransformStamped publish_tf;
    bool relabel_ok = false;

    try {
      if (use_latest_tf_) {
        publish_tf = tf_buffer_.lookupTransform(
          grid_publish_frame_, target_frame_, tf2::TimePointZero,
          tf2::durationFromSec(tf_timeout_s_));
      } else {
        publish_tf = tf_buffer_.lookupTransform(
          grid_publish_frame_, target_frame_, stamp,
          tf2::durationFromSec(tf_timeout_s_));
      }
      relabel_ok = true;
    } catch (const tf2::TransformException & ex) {
      RCLCPP_WARN_THROTTLE(
        get_logger(), *get_clock(), 2000,
        "Không gán lại được frame risk grid %s -> %s: %s. Tạm thời publish trong %s, "
        "layer phía costmap sẽ tự bỏ qua cycle này.",
        target_frame_.c_str(), grid_publish_frame_.c_str(), ex.what(), target_frame_.c_str());
    }

    if (relabel_ok) {
      const double yaw = tf2::getYaw(publish_tf.transform.rotation);
      const double cos_yaw = std::cos(yaw);
      const double sin_yaw = std::sin(yaw);

      const double local_x = grid.info.origin.position.x;
      const double local_y = grid.info.origin.position.y;

      const double world_x = publish_tf.transform.translation.x +
        cos_yaw * local_x - sin_yaw * local_y;
      const double world_y = publish_tf.transform.translation.y +
        sin_yaw * local_x + cos_yaw * local_y;

      tf2::Quaternion q_yaw_only;
      q_yaw_only.setRPY(0.0, 0.0, yaw);

      grid.header.frame_id = grid_publish_frame_;
      grid.info.origin.position.x = world_x;
      grid.info.origin.position.y = world_y;
      grid.info.origin.position.z = publish_tf.transform.translation.z;
      grid.info.origin.orientation = tf2::toMsg(q_yaw_only);
    }

    return grid;
  }

  void logStats(
    const rclcpp::Time & now,
    size_t finite_count,
    size_t roi_count,
    size_t gaussian_count,
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
      "GHRF risk: finite=%zu roi=%zu gaussian=%zu accepted_cells=%zu memory=%zu output=%zu",
      finite_count,
      roi_count,
      gaussian_count,
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
    size_t gaussian_count = 0;
    size_t accepted_cells = 0;

    processCloud(
      msg, tf, now,
      finite_count,
      roi_count,
      gaussian_count,
      accepted_cells);

    pruneMemory(now);

    const auto active_points = collectActiveRiskPoints(now);

    auto cloud_msg = makeCloudMsg(active_points, now);
    cloud_pub_->publish(cloud_msg);

    if (publish_risk_grid_) {
      auto grid_msg = makeRiskGridMsg(active_points, now);
      grid_pub_->publish(grid_msg);
    }

    last_publish_valid_ = true;
    last_publish_time_ = now;

    logStats(now, finite_count, roi_count, gaussian_count, accepted_cells, active_points.size());
  }
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<HeightRiskProjector>());
  rclcpp::shutdown();
  return 0;
}