#include "amr_costmap_plugins/ghrf_layer.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <memory>
#include <string>

#include "nav2_costmap_2d/cost_values.hpp"
#include "pluginlib/class_list_macros.hpp"
#include "tf2/utils.h"

namespace amr_costmap_plugins
{

namespace
{
// Cost tối đa layer này có thể ghi vào master_grid. Trùng với giải thích
// trong nav2_params_fusion.yaml: 100 (risk max) * 2.52 (max_cost_scale) = 252,
// tức LETHAL_OBSTACLE - 2, để không bao giờ tự ý đánh dấu LETHAL/INSCRIBED
// (việc đó để dành cho obstacle_layer/inflation_layer thật sự).
constexpr unsigned char kMaxRiskCost = nav2_costmap_2d::LETHAL_OBSTACLE - 2;
}  // namespace

GHRFLayer::GHRFLayer()
: has_grid_(false),
  bound_min_x_(0.0),
  bound_min_y_(0.0),
  bound_max_x_(0.0),
  bound_max_y_(0.0),
  has_bounds_(false),
  risk_topic_("/ghrf_risk_grid"),
  max_cost_scale_(2.52),
  grid_timeout_s_(0.6)
{
}

void GHRFLayer::onInitialize()
{
  auto node = node_.lock();
  if (!node) {
    throw std::runtime_error("GHRFLayer: không lock được node trong onInitialize()");
  }

  // Theo đúng pattern declareParameter() + get_parameter(name_ + "." + key)
  // mà các layer built-in của Nav2 (ObstacleLayer, InflationLayer, ...) dùng.
  declareParameter("enabled", rclcpp::ParameterValue(true));
  declareParameter("risk_topic", rclcpp::ParameterValue(risk_topic_));
  declareParameter("max_cost_scale", rclcpp::ParameterValue(max_cost_scale_));
  declareParameter("grid_timeout", rclcpp::ParameterValue(grid_timeout_s_));

  node->get_parameter(name_ + "." + "enabled", enabled_);
  node->get_parameter(name_ + "." + "risk_topic", risk_topic_);
  node->get_parameter(name_ + "." + "max_cost_scale", max_cost_scale_);
  node->get_parameter(name_ + "." + "grid_timeout", grid_timeout_s_);

  current_ = true;

  rclcpp::QoS qos(rclcpp::KeepLast(1));
  qos.reliable();
  qos.durability_volatile();

  risk_sub_ = node->create_subscription<nav_msgs::msg::OccupancyGrid>(
    risk_topic_, qos,
    std::bind(&GHRFLayer::riskGridCallback, this, std::placeholders::_1));

  RCLCPP_INFO(
    node->get_logger(),
    "GHRFLayer '%s' đã khởi tạo: risk_topic=%s, max_cost_scale=%.3f, grid_timeout=%.2fs",
    name_.c_str(), risk_topic_.c_str(), max_cost_scale_, grid_timeout_s_);
}

void GHRFLayer::riskGridCallback(const nav_msgs::msg::OccupancyGrid::SharedPtr msg)
{
  // Tính trước bounding box (world frame) của grid ngay trong callback, để
  // updateBounds() ở update-thread không phải lặp lại rotate+translate mỗi cycle.
  const double yaw = tf2::getYaw(msg->info.origin.orientation);
  const double cos_yaw = std::cos(yaw);
  const double sin_yaw = std::sin(yaw);
  const double ox = msg->info.origin.position.x;
  const double oy = msg->info.origin.position.y;
  const double w = msg->info.width * msg->info.resolution;
  const double h = msg->info.height * msg->info.resolution;

  // 4 góc của grid trong frame cục bộ của nó (trước khi rotate+translate).
  const double local_x[4] = {0.0, w, 0.0, w};
  const double local_y[4] = {0.0, 0.0, h, h};

  double min_x = std::numeric_limits<double>::max();
  double min_y = std::numeric_limits<double>::max();
  double max_x = std::numeric_limits<double>::lowest();
  double max_y = std::numeric_limits<double>::lowest();

  for (int i = 0; i < 4; ++i) {
    const double wx = ox + local_x[i] * cos_yaw - local_y[i] * sin_yaw;
    const double wy = oy + local_x[i] * sin_yaw + local_y[i] * cos_yaw;
    min_x = std::min(min_x, wx);
    min_y = std::min(min_y, wy);
    max_x = std::max(max_x, wx);
    max_y = std::max(max_y, wy);
  }

  std::lock_guard<std::mutex> lock(grid_mutex_);
  latest_grid_ = msg;
  last_update_time_ = rclcpp::Time(msg->header.stamp);
  has_grid_ = true;
  bound_min_x_ = min_x;
  bound_min_y_ = min_y;
  bound_max_x_ = max_x;
  bound_max_y_ = max_y;
  has_bounds_ = true;
}

void GHRFLayer::updateBounds(
  double /*robot_x*/, double /*robot_y*/, double /*robot_yaw*/,
  double * min_x, double * min_y, double * max_x, double * max_y)
{
  if (!enabled_) {
    return;
  }

  std::lock_guard<std::mutex> lock(grid_mutex_);
  if (!has_bounds_) {
    return;
  }

  *min_x = std::min(*min_x, bound_min_x_);
  *min_y = std::min(*min_y, bound_min_y_);
  *max_x = std::max(*max_x, bound_max_x_);
  *max_y = std::max(*max_y, bound_max_y_);
}

void GHRFLayer::updateCosts(
  nav2_costmap_2d::Costmap2D & master_grid,
  int min_i, int min_j, int max_i, int max_j)
{
  if (!enabled_) {
    return;
  }

  auto node = node_.lock();
  if (!node) {
    return;
  }

  // Copy shared_ptr + timestamp ra khỏi mutex càng sớm càng tốt, tránh giữ
  // lock trong lúc lặp toàn bộ grid (có thể vài nghìn cell).
  nav_msgs::msg::OccupancyGrid::SharedPtr grid;
  rclcpp::Time grid_time;
  {
    std::lock_guard<std::mutex> lock(grid_mutex_);
    if (!has_grid_) {
      return;
    }
    grid = latest_grid_;
    grid_time = last_update_time_;
  }

  const double age_s = (node->now() - grid_time).seconds();
  if (age_s > grid_timeout_s_) {
    RCLCPP_WARN_THROTTLE(
      node->get_logger(), *node->get_clock(), 5000,
      "GHRFLayer '%s': risk grid quá cũ (%.2fs > %.2fs), bỏ qua cycle này.",
      name_.c_str(), age_s, grid_timeout_s_);
    return;
  }

  if (grid->header.frame_id != layered_costmap_->getGlobalFrameID()) {
    RCLCPP_WARN_THROTTLE(
      node->get_logger(), *node->get_clock(), 5000,
      "GHRFLayer '%s': frame_id của grid ('%s') khác global frame ('%s'), "
      "bỏ qua cycle này (height_risk_projector relabel sai frame?).",
      name_.c_str(), grid->header.frame_id.c_str(),
      layered_costmap_->getGlobalFrameID().c_str());
    return;
  }

  // Không cần TF lookup ở đây: height_risk_projector đã relabel origin của
  // grid sang đúng global_frame khi publish, nên chỉ cần rotate+translate
  // toạ độ cục bộ theo origin/yaw có sẵn trong message.
  const double yaw = tf2::getYaw(grid->info.origin.orientation);
  const double cos_yaw = std::cos(yaw);
  const double sin_yaw = std::sin(yaw);
  const double ox = grid->info.origin.position.x;
  const double oy = grid->info.origin.position.y;
  const double res = grid->info.resolution;
  const unsigned int gw = grid->info.width;
  const unsigned int gh = grid->info.height;

  for (unsigned int gy = 0; gy < gh; ++gy) {
    for (unsigned int gx = 0; gx < gw; ++gx) {
      const int8_t value = grid->data[gy * gw + gx];
      if (value <= 0) {
        // <=0: cell rỗng hoặc unknown (-1) — không có gì để mark.
        continue;
      }

      const double lx = (gx + 0.5) * res;
      const double ly = (gy + 0.5) * res;
      const double wx = ox + lx * cos_yaw - ly * sin_yaw;
      const double wy = oy + lx * sin_yaw + ly * cos_yaw;

      unsigned int mx, my;
      if (!master_grid.worldToMap(wx, wy, mx, my)) {
        continue;
      }
      if (static_cast<int>(mx) < min_i || static_cast<int>(mx) >= max_i ||
        static_cast<int>(my) < min_j || static_cast<int>(my) >= max_j)
      {
        continue;
      }

      const double scaled = static_cast<double>(value) * max_cost_scale_;
      const double clamped = std::min(scaled, static_cast<double>(kMaxRiskCost));
      const unsigned char new_cost = static_cast<unsigned char>(std::max(1.0, clamped));

      const unsigned char existing = master_grid.getCost(mx, my);
      if (existing == nav2_costmap_2d::NO_INFORMATION || new_cost > existing) {
        master_grid.setCost(mx, my, new_cost);
      }
    }
  }
}

void GHRFLayer::reset()
{
  std::lock_guard<std::mutex> lock(grid_mutex_);
  latest_grid_.reset();
  has_grid_ = false;
  has_bounds_ = false;
  current_ = true;
}

void GHRFLayer::onFootprintChanged()
{
  // Không cần làm gì: risk grid không phụ thuộc kích thước/hình dạng footprint.
}

}  // namespace amr_costmap_plugins

PLUGINLIB_EXPORT_CLASS(amr_costmap_plugins::GHRFLayer, nav2_costmap_2d::Layer)