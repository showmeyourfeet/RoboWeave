# Unique object identifier
string object_id

# Object category (e.g. "cup", "bottle")
string category

# The query string that matched this detection
string matched_query

# 2D bounding box in image coordinates [x_min, y_min, x_max, y_max]
int32[] bbox_2d

# Detection confidence [0.0, 1.0]
float64 confidence

# Estimated pose in camera frame
geometry_msgs/Pose pose_camera

# Standard header with timestamp and frame_id
std_msgs/Header header
