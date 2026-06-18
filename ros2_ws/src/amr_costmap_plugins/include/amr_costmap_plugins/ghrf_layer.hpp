#ifndef AMR_COSTMAP_PLUGINS__GHRF_LAYER_HPP_
#define AMR_COSTMAP_PLUGINS__GHRF_LAYER_HPP_

#include <mutex>
#include <string>

#include "nav2_costmap_2d/costmap_2d.hpp"
#include "nav2_costmap_2d/layer.hpp"
#include "nav2_costmap_2d/layered_costmap.hpp"
#include "nav_msgs/msg/occupancy_grid.hpp"
#include "rclcpp/rclcpp.hpp"

namespace amr_costmap_plugins
{

// GHRFLayer: layer costmap đọc OccupancyGrid risk liên tục [0-100] do
// amr_pointcloud_filter/height_risk_projector publish (đã relabel sẵn sang
// global_frame của costmap), nhân với max_cost_scale_ để ra cost [1-252] rồi
// hợp nhất vào master_grid. Không cần TF lookup nào ở layer này: toàn bộ phép
// biến đổi frame đã được height_risk_projector làm một lần khi publish grid.
class GHRFLayer : public nav2_costmap_2d::Layer
{
public:
  GHRFLayer();

  void onInitialize() override;

  void updateBounds(
    double robot_x, double robot_y, double robot_yaw,
    double * min_x, double * min_y, double * max_x, double * max_y) override;

  void updateCosts(
    nav2_costmap_2d::Costmap2D & master_grid,
    int min_i, int min_j, int max_i, int max_j) override;

  void reset() override;

  // GHRF không phụ thuộc hình dạng footprint, nên đây là no-op (giữ override
  // để rõ ràng cho người đọc code/paper rằng đây là quyết định có chủ đích).
  void onFootprintChanged() override;

  bool isClearable() override {return true;}

private:
  void riskGridCallback(const nav_msgs::msg::OccupancyGrid::SharedPtr msg);

  rclcpp::Subscription<nav_msgs::msg::OccupancyGrid>::SharedPtr risk_sub_;

  // Bảo vệ truy cập latest_grid_/last_update_time_/bound_* giữa callback
  // (executor thread) và updateBounds()/updateCosts() (costmap update thread).
  std::mutex grid_mutex_;
  nav_msgs::msg::OccupancyGrid::SharedPtr latest_grid_;
  rclcpp::Time last_update_time_;
  bool has_grid_;

  // Bounding box (world frame) của grid mới nhất, tính trước trong callback
  // để updateBounds() chỉ cần merge, không phải lặp lại phép rotate+translate.
  double bound_min_x_;
  double bound_min_y_;
  double bound_max_x_;
  double bound_max_y_;
  bool has_bounds_;

  // Tham số cấu hình (đọc từ YAML qua declareParameter, xem onInitialize()).
  std::string risk_topic_;
  double max_cost_scale_;
  double grid_timeout_s_;
};

}  // namespace amr_costmap_plugins

#endif  // AMR_COSTMAP_PLUGINS__GHRF_LAYER_HPP_