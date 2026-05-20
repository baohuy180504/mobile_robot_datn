# AI alert message: fall, fire, smoke

builtin_interfaces/Time stamp

string alert_type        # FALL / FIRE / SMOKE / PERSON / UNKNOWN
float32 confidence
string message

bool active
geometry_msgs/PoseStamped robot_pose

string image_path
