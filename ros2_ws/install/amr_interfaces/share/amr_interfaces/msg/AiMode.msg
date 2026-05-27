# AMR operation mode

uint8 IDLE=0
uint8 NAV_TO_ZONE=1
uint8 FOLLOW_DETECTING=2
uint8 FOLLOW_ACTIVE=3
uint8 FOLLOW_STOPPED=4
uint8 RETURN_TO_ZONE=5
uint8 EMERGENCY_STOP=6
uint8 LOCALIZING=7

builtin_interfaces/Time stamp
uint8 mode
string mode_name
string detail
