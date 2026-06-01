import rclpy
from rclpy.node import Node

class BasicNode(Node):
    def __init__(self):
        # 初始化节点，节点名称为basic_node
        super().__init__('basic_node')
        # 创建一个定时器，每隔1秒调用一次timer_callback函数
        self.timer = self.create_timer(1.0, self.timer_callback)
        self.counter = 0

    def timer_callback(self):
        # 定时器回调函数，打印日志并更新计数器
        self.get_logger().info(f'节点运行中，当前计数: {self.counter}')
        self.counter += 1

def main(args=None):
    # 初始化rclpy库
    rclpy.init(args=args)
    # 创建节点实例
    basic_node = BasicNode()
    # 运行节点，保持节点持续运行
    rclpy.spin(basic_node)
    # 销毁节点并关闭rclpy
    basic_node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
