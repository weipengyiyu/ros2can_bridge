# CAN接收数据
bool        extended                        #帧类型  True扩展帧   Fase标准帧
uint8       dlc                             #数据长度
uint32      arbitration_id                  #CAN ID
uint8[8]    data                            #CAN 数据报文