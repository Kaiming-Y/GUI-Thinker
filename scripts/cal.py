def calculate_center(rectangle):
    if len(rectangle) != 4:
        raise ValueError("输入的矩形坐标必须包含4个数字: [X1, Y1, X2, Y2]")

    x1, y1, x2, y2 = rectangle
    center_x = (x1 + x2) // 2
    center_y = (y1 + y2) // 2

    return center_x, center_y


# 输入
rectangle = [
    514,
                            139,
                            587,
                            150
]

# 计算中心坐标
center = calculate_center(rectangle)
print(f"矩形的中心坐标为: {center}")
