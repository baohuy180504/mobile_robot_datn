# Locked person target for following behavior

std_msgs/Header header

int32 target_id
bool locked
bool lost

float32 confidence

# Bounding box on RGB image
int32 bbox_x
int32 bbox_y
int32 bbox_w
int32 bbox_h

# Estimated target position
geometry_msgs/PointStamped position_camera
geometry_msgs/PointStamped position_base
geometry_msgs/PointStamped position_map

float32 distance_m
float32 angle_rad
