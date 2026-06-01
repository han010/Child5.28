"""
GPS坐标转换模块

将GPS坐标(WGS84)转换为本地坐标系(以原点为0,0的UTM相对坐标)。
使用pyproj进行精确的投影转换。

坐标系说明:
- WGS84 (EPSG:4326): GPS原始坐标，经纬度
- UTM (如 EPSG:32651): 投影坐标，单位为米
- local: 以初始GPS位置为原点的相对坐标，单位为米
"""

from pyproj import Transformer


class CoordinateConverter:
    """GPS坐标 <-> 本地坐标 双向转换器"""

    def __init__(self, utm_zone: str = '51N'):
        """
        Args:
            utm_zone: UTM分区号，如 '51N' (中国东部)
        """
        self.utm_zone = utm_zone
        self._origin_lat: float | None = None
        self._origin_lon: float | None = None
        self._origin_utm_x: float | None = None
        self._origin_utm_y: float | None = None
        self._initialized = False

        # 创建 WGS84 → UTM 转换器
        epsg_code = self._utm_to_epsg(utm_zone)
        self._transformer = Transformer.from_crs(
            "EPSG:4326", epsg_code, always_xy=True
        )
        self._inverse_transformer = Transformer.from_crs(
            epsg_code, "EPSG:4326", always_xy=True
        )

    @staticmethod
    def _utm_to_epsg(zone: str) -> str:
        """UTM分区 → EPSG代码"""
        zone_num = int(zone[:-1])
        hemisphere = zone[-1].upper()
        if hemisphere == 'N':
            return f"EPSG:326{zone_num:02d}"
        else:
            return f"EPSG:327{zone_num:02d}"

    @property
    def initialized(self) -> bool:
        return self._initialized

    @property
    def origin_lat(self) -> float | None:
        return self._origin_lat

    @property
    def origin_lon(self) -> float | None:
        return self._origin_lon

    def set_origin(self, lat: float, lon: float):
        """设置本地坐标原点（通常是机器人启动时的GPS位置）"""
        self._origin_lat = lat
        self._origin_lon = lon
        self._origin_utm_x, self._origin_utm_y = self._transformer.transform(
            lon, lat
        )
        self._initialized = True

    def gps_to_local(self, lat: float, lon: float) -> tuple[float, float]:
        """
        GPS坐标 → 本地坐标(米)

        Args:
            lat: 纬度 (degrees)
            lon: 经度 (degrees)

        Returns:
            (x, y): 本地坐标，单位米，原点为初始GPS位置
        """
        if not self._initialized:
            raise RuntimeError("原点未初始化，请先调用 set_origin()")

        utm_x, utm_y = self._transformer.transform(lon, lat)
        local_x = utm_x - self._origin_utm_x
        local_y = utm_y - self._origin_utm_y
        return local_x, local_y

    def local_to_gps(self, x: float, y: float) -> tuple[float, float]:
        """
        本地坐标(米) → GPS坐标

        Args:
            x: 本地x坐标(米)
            y: 本地y坐标(米)

        Returns:
            (lat, lon): GPS坐标 (degrees)
        """
        if not self._initialized:
            raise RuntimeError("原点未初始化，请先调用 set_origin()")

        utm_x = self._origin_utm_x + x
        utm_y = self._origin_utm_y + y
        lon, lat = self._inverse_transformer.transform(utm_x, utm_y)
        return lat, lon
