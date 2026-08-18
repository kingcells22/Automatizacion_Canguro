import os
import sys
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection
import matplotlib.patheffects as path_effects

# Paleta de Colores Neón Corporativos "Slate Carbon & Glow"
MAP_BG = "#1A1A1A"
STATE_FILL_DEFAULT = "#222731"     # Tono Carbón Pizarra con contraste nítido sobre el fondo
STATE_EDGE_DEFAULT = "#3E4856"     # Líneas de frontera titanio elegantes
STATE_FILL_ACTIVE = "#3D3200"      # Estado resaltado
STATE_EDGE_ACTIVE = "#FFD700"      # Borde dorado brillante
STORE_DOT_COLOR = "#00E5FF"        # Cian Neón
STORE_DOT_TOP = "#FFD700"          # Oro Neón
STORE_HIGHLIGHT = "#FF0055"        # Magenta Neón

# Centroides para nombres de Estados
CENTROIDES_ESTADOS = {
    'Amazonas': (-65.8, 3.4, "Amazonas"),
    'Anzoátegui': (-64.4, 8.9, "Anzoátegui"),
    'Apure': (-68.5, 7.1, "Apure"),
    'Aragua': (-67.0, 9.8, "Aragua"),
    'Barinas': (-70.2, 8.2, "Barinas"),
    'Bolívar': (-63.5, 6.2, "Bolívar"),
    'Carabobo': (-68.05, 10.05, "Carabobo"),
    'Cojedes': (-68.3, 9.35, "Cojedes"),
    'Delta Amacuro': (-61.2, 8.7, "Delta Amacuro"),
    'Distrito Capital': (-66.92, 10.49, "Caracas"),
    'Falcón': (-69.8, 11.1, "Falcón"),
    'Guárico': (-66.4, 8.9, "Guárico"),
    'La Guaira': (-66.8, 10.62, "La Guaira"),
    'Lara': (-69.7, 10.05, "Lara"),
    'Mérida': (-71.3, 8.6, "Mérida"),
    'Miranda': (-66.4, 10.22, "Miranda"),
    'Monagas': (-63.3, 9.4, "Monagas"),
    'Nueva Esparta': (-63.9, 10.98, "Nva. Esparta"),
    'Portuguesa': (-69.3, 9.2, "Portuguesa"),
    'Sucre': (-63.2, 10.48, "Sucre"),
    'Táchira': (-72.1, 7.8, "Táchira"),
    'Trujillo': (-70.5, 9.38, "Trujillo"),
    'Yaracuy': (-68.8, 10.3, "Yaracuy"),
    'Zulia': (-71.8, 10.2, "Zulia")
}

# Catálogo exhaustivo de ubicaciones de tiendas Canguro
LOCACIONES_TIENDAS = [
    ('AV LIBERTADOR CIUDAD BOLIVAR', 'Bolívar', 'Ciudad Bolívar', 8.13, -63.55),
    ('ACHAGUAS', 'Apure', 'Achaguas', 7.77, -68.23),
    ('ANACO', 'Anzoátegui', 'Anaco', 9.43, -64.46),
    ('ALTAGRACIA DEL ORITUCO', 'Guárico', 'Altagracia de Orituco', 9.86, -66.38),
    ('AEDOS TOCUYITO', 'Carabobo', 'Tocuyito', 10.14, -68.08),
    ('TOCUYITO', 'Carabobo', 'Tocuyito', 10.14, -68.08),
    ('ANTIMANO', 'Distrito Capital', 'Caracas (Antímano)', 10.47, -66.96),
    ('APURE', 'Apure', 'San Fernando de Apure', 7.89, -67.47),
    ('ALTA VISTA', 'Bolívar', 'Puerto Ordaz', 8.29, -62.74),
    ('AVENIDA MARINO', 'Sucre', 'Carúpano', 10.66, -63.25),
    ('BUENOS AIRES CANGURO', 'Distrito Capital', 'Caracas', 10.49, -66.90),
    ('BISCUCUY', 'Portuguesa', 'Biscucuy', 9.36, -69.98),
    ('BARINAS CC DORADO', 'Barinas', 'Barinas (CC Dorado)', 8.62, -70.22),
    ('BARINAS SHOP', 'Barinas', 'Barinas', 8.63, -70.21),
    ('BARINAS', 'Barinas', 'Barinas', 8.63, -70.21),
    ('BARCELONA', 'Anzoátegui', 'Barcelona', 10.13, -64.69),
    ('BOCONO', 'Trujillo', 'Boconó', 9.24, -70.26),
    ('BEJUMA', 'Carabobo', 'Bejuma', 10.17, -68.26),
    ('BAILADORES', 'Mérida', 'Bailadores', 8.22, -71.82),
    ('BARRANCAS', 'Monagas', 'Barrancas del Orinoco', 8.70, -62.18),
    ('BARUTA', 'Miranda', 'Baruta', 10.43, -66.87),
    ('BAZAR VALENCIA', 'Carabobo', 'Valencia', 10.18, -68.00),
    ('BAZAR 1', 'Distrito Capital', 'Caracas (Centro)', 10.50, -66.91),
    ('BAZAR 2', 'Distrito Capital', 'Caracas (Centro)', 10.50, -66.91),
    ('BAZAR 3', 'Distrito Capital', 'Caracas (Centro)', 10.50, -66.91),
    ('BAZAR 4', 'Distrito Capital', 'Caracas (Centro)', 10.50, -66.91),
    ('CAGUA', 'Aragua', 'Cagua', 10.18, -67.46),
    ('CATIA LIFE PHONE', 'Distrito Capital', 'Caracas (Catia)', 10.51, -66.94),
    ('CATIA', 'Distrito Capital', 'Caracas (Catia)', 10.51, -66.94),
    ('CABIMAS', 'Zulia', 'Cabimas', 10.39, -71.44),
    ('CHABASQUEN', 'Portuguesa', 'Chabasquén', 9.43, -70.03),
    ('CABUDARE', 'Lara', 'Cabudare', 10.03, -69.26),
    ('CIUDAD BOLIVAR', 'Bolívar', 'Ciudad Bolívar', 8.13, -63.55),
    ('AVIADORES', 'Aragua', 'Maracay (Los Aviadores)', 10.19, -67.58),
    ('CAMEJO BARINAS', 'Barinas', 'Barinas', 8.63, -70.21),
    ('METROCENTER', 'Distrito Capital', 'Caracas (Capitolio)', 10.50, -66.91),
    ('CAICARA DEL ORINOCO', 'Bolívar', 'Caicara del Orinoco', 7.62, -66.16),
    ('TAMANACO SEGUNDO', 'Miranda', 'Caracas (CCCT)', 10.48, -66.85),
    ('TAMANACO', 'Miranda', 'Caracas (CCCT)', 10.48, -66.85),
    ('CANDELARIA', 'Distrito Capital', 'Caracas (La Candelaria)', 10.50, -66.90),
    ('CEDENO', 'Carabobo', 'Valencia (Av. Cedeño)', 10.19, -68.00),
    ('CENDIS MAYOR', 'Miranda', 'Caracas', 10.48, -66.86),
    ('CENDIS SHOWROOM', 'Miranda', 'Caracas', 10.48, -66.86),
    ('CHACAO', 'Miranda', 'Caracas (Chacao)', 10.49, -66.85),
    ('CHICHIRIVICHE', 'Falcón', 'Chichiriviche', 10.93, -68.27),
    ('CHIVACOA', 'Yaracuy', 'Chivacoa', 10.16, -68.89),
    ('CHARALLAVE', 'Miranda', 'Charallave', 10.24, -66.86),
    ('CINCO DE JULIO', 'Zulia', 'Maracaibo (5 de Julio)', 10.66, -71.62),
    ('CALABOZO', 'Guárico', 'Calabozo', 8.93, -67.43),
    ('CALLAO', 'Bolívar', 'El Callao', 7.35, -61.82),
    ('COLONIA TOVAR', 'Aragua', 'Colonia Tovar', 10.41, -67.28),
    ('CUA', 'Miranda', 'Cúa', 10.16, -66.88),
    ('COMERCIO', 'Distrito Capital', 'Caracas (Centro)', 10.50, -66.91),
    ('CUMANACOA', 'Sucre', 'Cumanacoa', 10.25, -63.91),
    ('COSMOS SHOP', 'Lara', 'Barquisimeto (CC Cosmos)', 10.06, -69.32),
    ('SAN CARLOS', 'Cojedes', 'San Carlos', 9.66, -68.58),
    ('CORO', 'Falcón', 'Coro', 11.41, -69.67),
    ('CARUPANO', 'Sucre', 'Carúpano', 10.66, -63.25),
    ('CLARINES', 'Anzoátegui', 'Clarines', 9.94, -65.17),
    ('CARIPE', 'Monagas', 'Caripe', 10.17, -63.50),
    ('CARORA', 'Lara', 'Carora', 10.17, -70.08),
    ('CARIPITO', 'Monagas', 'Caripito', 10.12, -63.10),
    ('CAJA SECA', 'Zulia', 'Caja Seca', 9.15, -71.09),
    ('CANTAURA', 'Anzoátegui', 'Cantaura', 9.31, -64.36),
    ('CITY 1', 'Distrito Capital', 'Caracas (City Market)', 10.49, -66.87),
    ('CITY 2', 'Distrito Capital', 'Caracas (City Market)', 10.49, -66.87),
    ('CITY 3', 'Distrito Capital', 'Caracas (City Market)', 10.49, -66.87),
    ('CARTANAL', 'Miranda', 'Cartanal', 10.21, -66.73),
    ('CEMENTERIO', 'Distrito Capital', 'Caracas (El Cementerio)', 10.48, -66.92),
    ('CUMANA', 'Sucre', 'Cumaná', 10.45, -64.17),
    ('CAUCAGUA', 'Miranda', 'Caucagua', 10.28, -66.39),
    ('DUACA', 'Lara', 'Duaca', 10.29, -69.16),
    ('EL CUJI', 'Lara', 'Barquisimeto (El Cují)', 10.14, -69.31),
    ('ECOMMERCE', 'Distrito Capital', 'Venta Digital / Caracas', 10.49, -66.90),
    ('EJIDO', 'Mérida', 'Ejido', 8.55, -71.24),
    ('ELORZA', 'Apure', 'Elorza', 7.06, -69.50),
    ('EL MANTECO', 'Bolívar', 'El Manteco', 7.37, -62.47),
    ('FLOR AMARILLO', 'Carabobo', 'Valencia (Flor Amarillo)', 10.16, -67.92),
    ('FREEMARKET 2', 'Carabobo', 'Naguanagua (Free Market)', 10.25, -68.01),
    ('FREEMARKET', 'Carabobo', 'Naguanagua (Free Market)', 10.25, -68.01),
    ('FORUM CHARALLAVE', 'Miranda', 'Charallave (Forum)', 10.24, -66.86),
    ('FORUM GUATIRE', 'Miranda', 'Guatire (Forum)', 10.47, -66.54),
    ('FORUM IPSFA', 'Distrito Capital', 'Caracas (IPSFA)', 10.48, -66.89),
    ('FORUM PARAISO', 'Distrito Capital', 'Caracas (El Paraíso)', 10.48, -66.93),
    ('FORUM PLAZA VENEZUELA', 'Distrito Capital', 'Caracas (Plaza Vzla)', 10.49, -66.88),
    ('GUACARA', 'Carabobo', 'Guacara', 10.23, -67.88),
    ('GUIRIA', 'Sucre', 'Güiria', 10.58, -62.30),
    ('GUANARITO', 'Portuguesa', 'Guanarito', 8.70, -69.21),
    ('GUANARE', 'Portuguesa', 'Guanare', 9.04, -69.74),
    ('GUANTA', 'Anzoátegui', 'Guanta', 10.24, -64.59),
    ('GUASIPATI', 'Bolívar', 'Guasipati', 7.47, -61.90),
    ('GUARENAS', 'Miranda', 'Guarenas', 10.46, -66.61),
    ('GUATIRE', 'Miranda', 'Guatire', 10.47, -66.54),
    ('GATO NEGRO', 'Distrito Capital', 'Caracas (Catia Gato Negro)', 10.51, -66.93),
    ('HIGUEROTE', 'Miranda', 'Higuerote', 10.49, -66.10),
    ('IGUALDAD', 'Bolívar', 'Ciudad Bolívar (Calle Igualdad)', 8.13, -63.55),
    ('LA BANDERA', 'Distrito Capital', 'Caracas (La Bandera)', 10.48, -66.91),
    ('LECHERIA', 'Anzoátegui', 'Lechería', 10.20, -64.69),
    ('LLANERO', 'Portuguesa', 'Acarigua (CC Llanero)', 9.56, -69.20),
    ('LA MARRON', 'Distrito Capital', 'Caracas (La Marrón)', 10.50, -66.91),
    ('LA PARAGUA', 'Bolívar', 'La Paragua', 6.84, -63.33),
    ('MACHIQUES', 'Zulia', 'Machiques', 10.06, -72.55),
    ('MARACAY ESTACION CENTRAL', 'Aragua', 'Maracay (Estación Central)', 10.24, -67.59),
    ('MARACAY', 'Aragua', 'Maracay', 10.24, -67.60),
    ('MINAS DE BARUTA', 'Miranda', 'Baruta (Las Minas)', 10.43, -66.86),
    ('MARGARITA', 'Nueva Esparta', 'Porlamar (Margarita)', 10.96, -63.85),
    ('MENE GRANDE', 'Zulia', 'Mene Grande', 9.82, -70.93),
    ('MERIDA', 'Mérida', 'Mérida', 8.59, -71.14),
    ('MOJAN', 'Zulia', 'San Rafael de El Moján', 10.96, -71.74),
    ('MACROCENTRO 1', 'Bolívar', 'Puerto Ordaz (Macrocentro)', 8.29, -62.73),
    ('MACROCENTRO 2', 'Bolívar', 'Puerto Ordaz (Macrocentro)', 8.29, -62.73),
    ('MONAY', 'Trujillo', 'Monay', 9.53, -70.47),
    ('MARKET PLACE CANGURO', 'Distrito Capital', 'Caracas (Digital)', 10.49, -66.90),
    ('MORON', 'Carabobo', 'Morón', 10.49, -68.20),
    ('MANTECAL', 'Apure', 'Mantecal', 7.56, -69.14),
    ('METROPOLIS', 'Carabobo', 'Valencia (CC Metrópolis)', 10.20, -67.96),
    ('MATURIN', 'Monagas', 'Maturín', 9.75, -63.18),
    ('MOVISTAR BELLA VISTA', 'Zulia', 'Maracaibo (Bella Vista)', 10.66, -71.61),
    ('MOVISTAR LAS GARZAS', 'Anzoátegui', 'Lechería (Las Garzas)', 10.19, -64.67),
    ('MOVISTAR LAS DELICIAS', 'Aragua', 'Maracay (Las Delicias)', 10.26, -67.59),
    ('MOVISTAR LOS LEONES', 'Lara', 'Barquisimeto (Los Leones)', 10.07, -69.29),
    ('MOVISTAR LA VINA', 'Carabobo', 'Valencia (La Viña)', 10.22, -68.01),
    ('MOVISTAR SAN CRISTOBAL', 'Táchira', 'San Cristóbal', 7.77, -72.23),
    ('NIRGUA', 'Yaracuy', 'Nirgua', 10.15, -68.57),
    ('NAIGUATA', 'La Guaira', 'Naiguatá', 10.61, -66.74),
    ('OCUMARE DEL TUY', 'Miranda', 'Ocumare del Tuy', 10.11, -66.77),
    ('CIUDAD OJEDA', 'Zulia', 'Ciudad Ojeda', 10.21, -71.31),
    ('OSPINO', 'Portuguesa', 'Ospino', 9.30, -69.45),
    ('ORINOKIA', 'Bolívar', 'Puerto Ordaz (Orinokia Mall)', 8.29, -62.74),
    ('PEDRAZA', 'Barinas', 'Ciudad Bolivia (Pedraza)', 8.34, -70.57),
    ('PUNTA DE MATA', 'Monagas', 'Punta de Mata', 9.69, -63.63),
    ('PUNTO FIJO', 'Falcón', 'Punto Fijo', 11.70, -70.20),
    ('PALO NEGRO', 'Aragua', 'Palo Negro', 10.17, -67.54),
    ('PUERTO LA CRUZ', 'Anzoátegui', 'Puerto La Cruz', 10.22, -64.63),
    ('PLAZA MAYOR LECHERIA', 'Anzoátegui', 'Lechería (Plaza Mayor)', 10.20, -64.68),
    ('PROPATRIA', 'Distrito Capital', 'Caracas (Propatria)', 10.52, -66.95),
    ('PARIAGUAN', 'Anzoátegui', 'Pariaguán', 8.85, -64.71),
    ('PUERTO PIRITU', 'Anzoátegui', 'Puerto Píritu', 10.06, -65.03),
    ('ACARIGUA', 'Portuguesa', 'Acarigua', 9.56, -69.20),
    ('PUERTO AYACUCHO', 'Amazonas', 'Puerto Ayacucho', 5.66, -67.63),
    ('PUERTO CABELLO', 'Carabobo', 'Puerto Cabello', 10.47, -68.01),
    ('PETARE 1', 'Miranda', 'Caracas (Petare)', 10.48, -66.81),
    ('PETARE 3', 'Miranda', 'Caracas (Petare)', 10.48, -66.81),
    ('PETARE', 'Miranda', 'Caracas (Petare)', 10.48, -66.81),
    ('QUIBOR', 'Lara', 'Quíbor', 9.93, -69.62),
    ('QUINTA CRESPO', 'Distrito Capital', 'Caracas (Quinta Crespo)', 10.49, -66.92),
    ('RIO CHICO', 'Miranda', 'Río Chico', 10.32, -65.98),
    ('SAMBIL CANDELARIA', 'Distrito Capital', 'Caracas (Sambil Candelaria)', 10.50, -66.90),
    ('SAMBIL CHACAO', 'Miranda', 'Caracas (Sambil Chacao)', 10.49, -66.85),
    ('SAMBIL LARA', 'Lara', 'Barquisimeto (Sambil)', 10.07, -69.29),
    ('SAMBIL MARGARITA', 'Nueva Esparta', 'Pampatar (Sambil)', 10.99, -63.81),
    ('SAMBIL PUNTO FIJO', 'Falcón', 'Punto Fijo (Sambil)', 11.68, -70.19),
    ('SAMBIL VALENCIA', 'Carabobo', 'Valencia (Sambil)', 10.24, -68.00),
    ('SAMBIL ZULIA', 'Zulia', 'Maracaibo (Sambil)', 10.69, -71.63),
    ('SANTA BARBARA', 'Zulia', 'Santa Bárbara del Zulia', 8.98, -71.91),
    ('SABANA CITY', 'Distrito Capital', 'Caracas (Sabana Grande)', 10.49, -66.87),
    ('EL SOMBRERO', 'Guárico', 'El Sombrero', 9.38, -67.06),
    ('SAN CASIMIRO', 'Aragua', 'San Casimiro', 9.99, -67.02),
    ('SOCOPO', 'Barinas', 'Socopó', 8.24, -70.78),
    ('SANTA ELENA DE UAIREN', 'Bolívar', 'Santa Elena de Uairén', 4.60, -61.11),
    ('SAN FELIX', 'Bolívar', 'San Félix', 8.36, -62.66),
    ('SABANA GRANDE', 'Distrito Capital', 'Caracas (Sabana Grande)', 10.49, -66.87),
    ('SAN JUAN DE LOS MORROS', 'Guárico', 'San Juan de los Morros', 9.91, -67.35),
    ('SABANA MENDOZA', 'Trujillo', 'Sabana de Mendoza', 9.44, -70.76),
    ('SIERRA MAESTRA', 'Zulia', 'San Francisco (Sierra Maestra)', 10.59, -71.65),
    ('SANARE', 'Lara', 'Sanare', 9.75, -69.66),
    ('SABANETA', 'Barinas', 'Sabaneta', 8.76, -69.93),
    ('SAN RAFAEL DE ONOTO', 'Portuguesa', 'San Rafael de Onoto', 9.78, -68.98),
    ('SANTA LUCIA', 'Miranda', 'Santa Lucía', 10.30, -66.66),
    ('SANTA RITA ARAGUA', 'Aragua', 'Santa Rita', 10.20, -67.56),
    ('SANTA TERESA DEL TUY', 'Miranda', 'Santa Teresa del Tuy', 10.23, -66.66),
    ('TEMBLADOR', 'Monagas', 'Temblador', 9.02, -62.62),
    ('TUCACAS', 'Falcón', 'Tucacas', 10.79, -68.32),
    ('TUCUPIDO', 'Guárico', 'Tucupido', 9.28, -65.77),
    ('TOCUYO', 'Lara', 'El Tocuyo', 9.79, -69.80),
    ('TUCUPITA', 'Delta Amacuro', 'Tucupita', 9.06, -62.05),
    ('LOS TEQUES TRES', 'Miranda', 'Los Teques', 10.34, -67.04),
    ('LOS TEQUES DOS', 'Miranda', 'Los Teques', 10.34, -67.04),
    ('LOS TEQUES', 'Miranda', 'Los Teques', 10.34, -67.04),
    ('EL TIGRITO', 'Anzoátegui', 'El Tigrito (San José de Guanipa)', 8.88, -64.17),
    ('TIGRE', 'Anzoátegui', 'El Tigre', 8.89, -64.25),
    ('TACHIRA', 'Táchira', 'San Cristóbal', 7.77, -72.23),
    ('TRUJILLO', 'Trujillo', 'Trujillo', 9.37, -70.44),
    ('TURMERO', 'Aragua', 'Turmero', 10.23, -67.47),
    ('TUMEREMO', 'Bolívar', 'Tumeremo', 7.30, -61.50),
    ('PLAZA VENEZUELA', 'Distrito Capital', 'Caracas (Plaza Venezuela)', 10.49, -66.88),
    ('TINAQUILLO', 'Cojedes', 'Tinaquillo', 9.92, -69.06),
    ('TUREN', 'Portuguesa', 'Turén', 9.33, -69.12),
    ('VALERA', 'Trujillo', 'Valera', 9.32, -70.60),
    ('UNARE', 'Bolívar', 'Puerto Ordaz (Unare)', 8.30, -62.77),
    ('UPATA', 'Bolívar', 'Upata', 8.01, -62.40),
    ('URDANETA FIX', 'Distrito Capital', 'Caracas (Av. Urdaneta)', 10.50, -66.91),
    ('URDANETA', 'Distrito Capital', 'Caracas (Av. Urdaneta)', 10.50, -66.91),
    ('LA GUAIRA', 'La Guaira', 'La Guaira', 10.60, -66.93),
    ('VILLA DE CURA', 'Aragua', 'Villa de Cura', 10.04, -67.48),
    ('VALLE DE LA PASCUA', 'Guárico', 'Valle de la Pascua', 9.22, -66.01),
    ('LA VEGA', 'Distrito Capital', 'Caracas (La Vega)', 10.47, -66.95),
    ('VIGIA', 'Mérida', 'El Vigía', 8.62, -71.65),
    ('EL VALLE', 'Distrito Capital', 'Caracas (El Valle)', 10.46, -66.90),
    ('LA VICTORIA', 'Aragua', 'La Victoria', 10.22, -67.33),
    ('SAN FELIPE', 'Yaracuy', 'San Felipe', 10.34, -68.74),
    ('YARITAGUA', 'Yaracuy', 'Yaritagua', 10.08, -69.13),
    ('ZARAZA', 'Guárico', 'Zaraza', 9.35, -65.32)
]

# Caché en memoria para geometría de estados
_GEOJSON_CACHE = None

def _obtener_ruta_geojson():
    """Retorna la ruta segura a venezuela.geojson compatible con .exe y desarrollo"""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(base_path, "assets", "venezuela.geojson")

def cargar_geometria_venezuela():
    """Carga y parsea los polígonos de los estados de Venezuela una sola vez"""
    global _GEOJSON_CACHE
    if _GEOJSON_CACHE is not None:
        return _GEOJSON_CACHE

    ruta = _obtener_ruta_geojson()
    if not os.path.exists(ruta):
        _GEOJSON_CACHE = []
        return _GEOJSON_CACHE

    try:
        with open(ruta, 'r', encoding='utf-8', errors='ignore') as f:
            data = json.load(f)

        estados = []
        for feat in data.get('features', []):
            nombre = feat.get('properties', {}).get('shapeName', 'Desconocido')
            geom = feat.get('geometry', {})
            gtype = geom.get('type', '')
            coords = geom.get('coordinates', [])
            
            poligonos = []
            if gtype == 'Polygon':
                for ring in coords:
                    poligonos.append(np.array(ring))
            elif gtype == 'MultiPolygon':
                for poly in coords:
                    for ring in poly:
                        poligonos.append(np.array(ring))
                        
            estados.append({
                'nombre': nombre,
                'poligonos': poligonos
            })
            
        _GEOJSON_CACHE = estados
        return _GEOJSON_CACHE
    except Exception:
        _GEOJSON_CACHE = []
        return _GEOJSON_CACHE

def resolver_tienda(nombre_tienda):
    """
    Resuelve el nombre crudo de una tienda a (Estado, Ciudad, Lat, Lon, Nombre_Limpio).
    Totalmente resiliente a tiendas nuevas en períodos futuros.
    """
    if not nombre_tienda:
        return 'Distrito Capital', 'Caracas', 10.49, -66.90, 'TODAS'

    nombre_str = str(nombre_tienda).strip()
    limpio = nombre_str.upper()
    if ']' in limpio:
        limpio = limpio.split(']')[-1]
    limpio = limpio.replace('-', ' ').strip()

    # Búsqueda en catálogo de tiendas y ciudades
    for clave, edo, ciu, lat, lon in LOCACIONES_TIENDAS:
        if clave in limpio or clave in nombre_str.upper():
            return edo, ciu, lat, lon, limpio

    # Inferencia por coincidencia con nombre de estado
    for edo, (lat_c, lon_c, nom_c) in CENTROIDES_ESTADOS.items():
        if edo.upper() in limpio or nom_c.upper() in limpio:
            return edo, edo, lat_c, lon_c, limpio

    # Fallback default
    return 'Distrito Capital', 'Caracas', 10.49, -66.90, limpio

def dibujar_mapa_venezuela(ax, df_tiendas, tienda_seleccionada=None):
    """
    Dibuja el mapa vectorial de Venezuela en el eje Matplotlib con estética Dark Mode Neón.
    - Ilumina el estado y enfoca la tienda si está seleccionada.
    - Muestra puntos con brillo proporcional al ingreso en vista general.
    """
    ax.clear()
    ax.set_facecolor(MAP_BG)

    estados = cargar_geometria_venezuela()
    
    # Determinar si hay tienda seleccionada
    es_filtro_tienda = False
    edo_sel = None
    ciu_sel = None
    lat_sel = None
    lon_sel = None
    nom_tienda_sel = None
    ingreso_sel = 0.0

    if tienda_seleccionada and str(tienda_seleccionada).strip() not in ["", "Todas las Ciudades", "TODAS"]:
        es_filtro_tienda = True
        edo_sel, ciu_sel, lat_sel, lon_sel, nom_tienda_sel = resolver_tienda(tienda_seleccionada)
        if not df_tiendas.empty:
            match_t = df_tiendas[df_tiendas['CENTRO DE COSTO / TIENDA'] == tienda_seleccionada]
            if not match_t.empty and 'INGRESOS TOTALES (USD)' in match_t.columns:
                ingreso_sel = float(match_t['INGRESOS TOTALES (USD)'].values[0])

    # 1. Dibujar Polígonos de los Estados
    for estado in estados:
        nom_edo = estado['nombre']
        es_activo = es_filtro_tienda and (nom_edo.upper() == edo_sel.upper() or (edo_sel == 'Distrito Capital' and nom_edo == 'Distrito Capital'))
        
        color_fill = STATE_FILL_ACTIVE if es_activo else STATE_FILL_DEFAULT
        color_edge = STATE_EDGE_ACTIVE if es_activo else STATE_EDGE_DEFAULT
        lw = 1.4 if es_activo else 0.7
        alpha = 0.95 if es_activo else 0.85

        for poly_coords in estado['poligonos']:
            patch = Polygon(poly_coords, closed=True, facecolor=color_fill, edgecolor=color_edge, linewidth=lw, alpha=alpha, zorder=1)
            ax.add_patch(patch)

    # 2. Dibujar Etiquetas de Estados con Sombra Nítida para Alta Legibilidad
    for edo_key, (lon_c, lat_c, label_edo) in CENTROIDES_ESTADOS.items():
        es_activo = es_filtro_tienda and (edo_key.upper() == edo_sel.upper())
        color_txt = "#FFD700" if es_activo else "#99A5BC"
        weight = "bold"
        fontsize = 7.8 if es_activo else 6.6
        
        # Omitir nombres muy pequeños en zonas comprimidas si no está seleccionado
        if not es_activo and edo_key in ['Distrito Capital', 'La Guaira', 'Dependencias Federales']:
            continue
            
        txt_obj = ax.text(lon_c, lat_c, label_edo, color=color_txt, fontsize=fontsize, fontweight=weight, ha='center', va='center', zorder=3, alpha=0.95)
        txt_obj.set_path_effects([path_effects.withStroke(linewidth=2.2, foreground='#12151C')])

    # 3. Dibujar Puntos de Tiendas
    if es_filtro_tienda and lat_sel is not None:
        # Tienda Individual Seleccionada: Marcador Objetivo + Tarjeta Flotante
        # Efecto radar exterior
        ax.scatter([lon_sel], [lat_sel], s=350, facecolors='none', edgecolors=STORE_HIGHLIGHT, linewidth=2.5, alpha=0.85, zorder=5)
        ax.scatter([lon_sel], [lat_sel], s=120, color=STORE_DOT_TOP, edgecolors='#FFFFFF', linewidth=1.5, zorder=6)
        
        # Etiqueta / Badge Flotante Elegante
        texto_badge = f"TIENDA: {nom_tienda_sel}\nESTADO: {edo_sel} | {ciu_sel}\nINGRESOS: ${ingreso_sel:,.2f}"
        
        # Ajustar posición del badge para no salirse de los límites
        offset_x = 0.8 if lon_sel < -66.0 else -0.8
        offset_y = 0.8 if lat_sel < 9.5 else -0.8
        ha_align = 'left' if offset_x > 0 else 'right'
        
        ax.annotate(
            texto_badge,
            xy=(lon_sel, lat_sel),
            xytext=(lon_sel + offset_x, lat_sel + offset_y),
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#101318", edgecolor=STORE_DOT_TOP, linewidth=1.5, alpha=0.94),
            color="#FFFFFF",
            fontsize=7.5,
            fontweight="bold",
            ha=ha_align,
            va="center",
            arrowprops=dict(arrowstyle="->", color=STORE_DOT_TOP, lw=1.2),
            zorder=7
        )
        ax.set_title(f"Sede: {nom_tienda_sel} ({edo_sel})", color=STORE_DOT_TOP, pad=7, fontweight='bold', fontsize=11)

    else:
        # Vista General: Dibujar todas las tiendas activas con tamaño proporcional a ingresos
        ax.set_title("Presencia Nacional Canguro (Venezuela)", color='#FFFFFF', pad=7, fontweight='bold', fontsize=11)
        
        if not df_tiendas.empty and 'INGRESOS TOTALES (USD)' in df_tiendas.columns:
            lons = []
            lats = []
            sizes = []
            colores = []
            max_rev = df_tiendas['INGRESOS TOTALES (USD)'].max() if not df_tiendas.empty else 1
            if max_rev == 0: max_rev = 1

            for _, row in df_tiendas.iterrows():
                t_nombre = row['CENTRO DE COSTO / TIENDA']
                rev = float(row.get('INGRESOS TOTALES (USD)', 0))
                _, _, t_lat, t_lon, _ = resolver_tienda(t_nombre)
                
                # Tamaño de punto proporcional
                tam = 14 + (rev / max_rev) * 80
                lons.append(t_lon)
                lats.append(t_lat)
                sizes.append(tam)
                
                if rev >= max_rev * 0.5:
                    colores.append(STORE_DOT_TOP)
                elif rev >= max_rev * 0.2:
                    colores.append(STORE_HIGHLIGHT)
                else:
                    colores.append(STORE_DOT_COLOR)

            # Capa de resplandor suave
            ax.scatter(lons, lats, s=[s*1.6 for s in sizes], color=STORE_DOT_COLOR, alpha=0.18, zorder=4)
            # Puntos principales con micro-borde oscuro para nitidez
            ax.scatter(lons, lats, s=sizes, color=colores, edgecolors='#12151C', linewidth=0.6, alpha=0.82, zorder=5)
            
            # Badge de resumen en la esquina inferior izquierda
            total_sedes = len(df_tiendas)
            total_ingresos = df_tiendas['INGRESOS TOTALES (USD)'].sum()
            ax.text(
                -73.0, 1.2,
                f"Sedes Activas: {total_sedes}\nFacturación: ${total_ingresos:,.0f}",
                fontsize=7.5,
                color="#CCCCCC",
                fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.4", facecolor="#14171E", edgecolor="#2D3542", alpha=0.88),
                zorder=6
            )

    # Configuración de límites milimétricos para maximizar el tamaño del mapa
    ax.set_xlim(-73.38, -59.72)
    ax.set_ylim(0.60, 12.52)
    ax.set_aspect('equal')
    ax.axis('off')
