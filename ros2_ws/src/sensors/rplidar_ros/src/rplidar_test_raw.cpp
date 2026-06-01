// 简单的RPLIDAR测试程序 - 直接读取串口数据
// 编译: g++ -o rplidar_test_raw rplidar_test_raw.cpp

#include <iostream>
#include <fcntl.h>
#include <termios.h>
#include <unistd.h>
#include <cstring>
#include <sys/ioctl.h>
#include <linux/serial.h>

int main() {
    const char* port = "/dev/ttyUSB0";

    std::cout << "打开串口: " << port << std::endl;

    int fd = open(port, O_RDWR | O_NOCTTY | O_NDELAY);
    if (fd == -1) {
        std::cerr << "无法打开串口" << std::endl;
        return 1;
    }

    struct termios options;
    tcgetattr(fd, &options);

    // 设置115200波特率
    cfsetispeed(&options, B115200);
    cfsetospeed(&options, B115200);

    // 8N1
    options.c_cflag &= ~PARENB;
    options.c_cflag &= ~CSTOPB;
    options.c_cflag &= ~CSIZE;
    options.c_cflag |= CS8;

    // 启用接收
    options.c_cflag |= (CLOCAL | CREAD);

    // 禁用流控
    options.c_cflag &= ~CRTSCTS;

    // 原始输入模式
    options.c_lflag &= ~(ICANON | ECHO | ECHOE | ISIG);

    // 原始输出模式
    options.c_oflag &= ~OPOST;

    // 禁用软件流控
    options.c_iflag &= ~(IXON | IXOFF | IXANY);

    // 设置超时 - 1秒超时
    options.c_cc[VTIME] = 10;
    options.c_cc[VMIN] = 0;

    tcsetattr(fd, TCSANOW, &options);

    // 启动电机 - 设置DTR为低
    int flags = fcntl(fd, F_GETFL, 0);
    fcntl(fd, F_SETFL, flags & ~O_NONBLOCK);

    int mcr = TIOCM_DTR;
    ioctl(fd, TIOCMBIC, &mcr);  // 清除DTR启动电机

    std::cout << "电机已启动（DTR=0），等待3秒让电机加速..." << std::endl;
    sleep(3);

    // 发送扫描命令
    unsigned char scan_cmd[] = {0xA5, 0x20};  // 标准扫描命令
    write(fd, scan_cmd, 2);

    std::cout << "发送扫描命令，读取数据（5秒）..." << std::endl;

    unsigned char buf[4096];
    int total_read = 0;
    time_t start_time = time(nullptr);

    while (time(nullptr) - start_time < 5) {
        int n = read(fd, buf, sizeof(buf));
        if (n > 0) {
            total_read += n;
            std::cout << "读取 " << n << " 字节，总共 " << total_read << " 字节" << std::endl;

            // 打印前几个字节
            if (total_read <= 100) {
                printf("数据: ");
                for (int i = 0; i < n && i < 20; i++) {
                    printf("%02X ", buf[i]);
                }
                printf("\n");
            }
        }
    }

    // 停止电机
    ioctl(fd, TIOCMBIS, &mcr);  // 设置DTR停止电机

    close(fd);

    if (total_read > 0) {
        std::cout << "\n✓ 雷达正在发送数据！共接收 " << total_read << " 字节" << std::endl;
        std::cout << "如果ROS2仍然超时，问题可能在SDK层面" << std::endl;
    } else {
        std::cout << "\n✗ 没有接收到任何数据" << std::endl;
        std::cout << "可能的问题：" << std::endl;
        std::cout << "  1. 雷达电机没有旋转" << std::endl;
        std::cout << "  2. USB线缆有问题" << std::endl;
        std::cout << "  3. 雷达硬件故障" << std::endl;
    }

    return 0;
}
