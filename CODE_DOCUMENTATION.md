# Código Documentado: Herramienta de Optimización de Trenes

Este documento explica línea por línea el funcionamiento del código implementado para la optimización de billetes de tren españoles.

## Estructura del Proyecto

```
src/trenes_tool/
├── __init__.py          # Inicialización del paquete
├── models.py            # Modelos de datos con Pydantic
├── scraper.py           # Web scraping con Playwright
├── optimizer.py         # Motor de optimización de precios
├── database.py          # Gestión de base de datos SQLite
└── cli.py               # Interfaz de línea de comandos
```

## 1. Modelos de Datos (`models.py`)

### Enums y Constantes

```python
class TrainType(str, Enum):
    """Tipos de trenes españoles disponibles."""
    AVE = "AVE"              # Alta Velocidad Española - trenes de alta velocidad
    AVLO = "AVLO"            # Marca low-cost de Renfe
    ALVIA = "ALVIA"          # Trenes híbridos alta velocidad/convencional
    ALTARIA = "ALTARIA"      # Trenes de larga distancia
    TALGO = "TALGO"          # Tecnología específica de trenes
    INTERCITY = "INTERCITY"   # Trenes intercity
    REGIONAL = "REGIONAL"     # Trenes regionales
    CERCANIAS = "CERCANIAS"   # Trenes de cercanías
```

**¿Por qué usar Enum?** Los enums proporcionan:
- Validación automática de valores
- Autocompletado en IDEs
- Prevención de errores tipográficos
- Documentación clara de opciones válidas

### Modelos Base

```python
class Station(BaseModel):
    """Modelo para estaciones de tren."""
    code: str = Field(..., description="Código de estación (ej: 'MADRI')")
    name: str = Field(..., description="Nombre de estación (ej: 'Madrid-Puerta de Atocha')")
    city: str = Field(..., description="Ciudad")
```

**Pydantic BaseModel**: Proporciona:
- Validación automática de tipos
- Serialización/deserialización JSON
- Documentación integrada con Field()
- Generación automática de esquemas

### Modelo de Ruta

```python
class TrainRoute(BaseModel):
    """Información completa de una ruta de tren."""
    origin: Station                    # Estación origen (objeto anidado)
    destination: Station               # Estación destino (objeto anidado)
    departure_time: datetime           # Hora de salida (con zona horaria)
    arrival_time: datetime             # Hora de llegada
    train_type: TrainType              # Tipo de tren (enum validado)
    train_number: str                  # Número identificador del tren
    duration_minutes: int              # Duración en minutos (calculado)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()  # Serialización ISO 8601
        }
```

**¿Por qué datetime en lugar de str?**
- Operaciones matemáticas (duración, comparaciones)
- Manejo automático de zonas horarias
- Validación de formato automática
- Facilita cálculos de optimización

### Modelo de Precio

```python
class PriceData(BaseModel):
    """Datos de precio histórico para análisis."""
    route: TrainRoute                          # Ruta asociada (referencia completa)
    price: Decimal                             # Precio en euros (precisión decimal)
    currency: str = Field(default="EUR")       # Moneda (siempre EUR para España)
    ticket_type: str                           # Tipo de billete ("Turista", "Preferente")
    availability: int                          # Asientos disponibles
    scraped_at: datetime = Field(default_factory=datetime.now)  # Timestamp de scraping
```

**¿Por qué Decimal en lugar de float?**
- Precisión exacta para cálculos monetarios
- Evita errores de redondeo de punto flotante
- Estándar para aplicaciones financieras

### Modelo de Optimización

```python
class OptimizationResult(BaseModel):
    """Resultado del análisis de optimización."""
    route_key: str                             # Identificador único ruta+fecha
    current_price: Decimal                     # Precio actual analizado
    recommendation: OptimizationRecommendation # Recomendación (enum)
    confidence: float = Field(..., ge=0.0, le=1.0)  # Confianza 0-1
    reasoning: str                             # Explicación humanamente legible
    suggested_action: str                      # Acción específica a tomar

    # Campos opcionales para análisis avanzado
    price_trend: Optional[str] = None          # "rising", "falling", "stable"
    optimal_purchase_window: Optional[str] = None  # Ventana óptima de compra
    days_until_departure: int                  # Días hasta la salida
    historical_low: Optional[Decimal] = None   # Precio histórico más bajo
    historical_high: Optional[Decimal] = None  # Precio histórico más alto
    price_volatility: Optional[float] = None   # Medida de volatilidad
```

**Validación con Field()**:
- `ge=0.0, le=1.0`: Garantiza que confianza esté entre 0 y 1
- Tipos Optional permiten campos no requeridos
- Documentación automática de restricciones

## 2. Web Scraping (`scraper.py`)

### Inicialización del Scraper

```python
class RenfeScraper:
    """Scraper especializado para el sitio web de Renfe."""

    BASE_URL = "https://www.renfe.com"        # URL base del sitio
    SEARCH_URL = "https://www.renfe.com/es/"  # URL específica de búsqueda

    def __init__(self, headless: bool = True, timeout: int = 30000):
        """
        Inicializa el scraper con configuración personalizable.

        Args:
            headless: Ejecutar navegador sin interfaz gráfica (True para producción)
            timeout: Tiempo límite para operaciones en milisegundos
        """
        self.headless = headless      # Modo headless para servidores
        self.timeout = timeout        # Timeout configurable
        self.browser: Optional[Browser] = None   # Instancia del navegador
        self.page: Optional[Page] = None         # Página actual
```

**¿Por qué Playwright?**
- JavaScript moderno soportado (SPAs)
- Múltiples navegadores (Chromium, Firefox, WebKit)
- API async/await nativa
- Screenshots y debugging integrados
- Mejor rendimiento que Selenium

### Context Managers

```python
async def __aenter__(self):
    """Método para usar 'async with RenfeScraper():'."""
    await self.start()
    return self

async def __aexit__(self, exc_type, exc_val, exc_tb):
    """Cleanup automático al salir del contexto."""
    await self.close()
```

**Ventajas del Context Manager**:
- Cleanup automático de recursos
- Previene memory leaks del navegador
- Código más limpio y legible
- Manejo de excepciones integrado

### Inicialización del Navegador

```python
async def start(self) -> None:
    """Inicia el navegador y configura una nueva página."""
    playwright = await async_playwright().start()           # Inicia Playwright
    self.browser = await playwright.chromium.launch(        # Lanza Chromium
        headless=self.headless
    )
    self.page = await self.browser.new_page()               # Nueva pestaña

    # User-Agent realista para evitar detección de bots
    await self.page.set_extra_http_headers({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36..."
    })
```

**Anti-detección**:
- User-Agent realista simula navegador humano
- Headers adicionales pueden incluir Accept-Language, etc.
- Delays aleatorios entre acciones (implementar si es necesario)

### Llenado de Formularios

```python
async def _fill_search_form(self, origin: str, destination: str, departure_date: date, return_date: Optional[date] = None) -> None:
    """Llena el formulario de búsqueda con múltiples estrategias."""

    # Esperamos que la página cargue completamente
    await self.page.wait_for_load_state("networkidle")

    # Array de selectores posibles para cada campo
    origin_selectors = [
        "#origen",                    # ID más común en español
        "#origin",                    # ID en inglés
        "input[name='origen']",       # Selector de atributo name
        "[placeholder*='Origen']",    # Selector de placeholder parcial
        "input[type='text']:first-child"  # Fallback posicional
    ]
```

**Estrategia Multi-Selector**:
- Robustez ante cambios en el sitio web
- Soporte para múltiples idiomas
- Fallbacks posicionales como última opción
- Logging detallado para debugging

### Lógica de Selección Inteligente

```python
# Intentamos cada selector hasta encontrar uno que funcione
origin_filled = False
for selector in origin_selectors:
    try:
        await self.page.wait_for_selector(selector, timeout=2000)  # Esperar elemento
        await self.page.fill(selector, origin)                     # Llenar campo
        await self.page.wait_for_timeout(1000)                    # Esperar autocomplete
        origin_filled = True
        logger.info(f"Origin filled using selector: {selector}")   # Log éxito
        break                                                      # Salir del loop
    except:
        continue                                                   # Probar siguiente selector

if not origin_filled:
    logger.warning("Could not find origin input field")          # Log warning
```

**¿Por qué try/except en bucle?**
- Sitios web cambian su estructura
- Diferentes versiones del sitio (A/B testing)
- Manejo graceful de errores
- Continuidad del proceso

### Manejo de Fechas

```python
# Múltiples formatos de fecha para compatibilidad
date_formats = [
    departure_date.strftime("%d/%m/%Y"),    # Formato español: 25/12/2024
    departure_date.strftime("%Y-%m-%d"),    # Formato ISO: 2024-12-25
    departure_date.strftime("%m/%d/%Y")     # Formato US: 12/25/2024
]

for date_format in date_formats:
    try:
        await self.page.fill(selector, date_format)
        date_filled = True
        logger.info(f"Date filled using format: {date_format}")
        break
    except:
        continue
```

**Múltiples Formatos**:
- Diferentes localizaciones del sitio
- Cambios en la implementación del calendario
- Compatibilidad internacional

## 3. Base de Datos (`database.py`)

### Diseño de Esquema

```python
def init_database(self) -> None:
    """Crea las tablas de la base de datos con relaciones normalizadas."""

    # Tabla de estaciones (datos maestros)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,    -- Clave primaria autoincrementada
            code TEXT UNIQUE NOT NULL,               -- Código único de estación
            name TEXT NOT NULL,                      -- Nombre completo
            city TEXT NOT NULL,                      -- Ciudad para agrupación
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- Auditoría
        )
    """)
```

**Normalización**:
- Estaciones separadas evita duplicación
- Códigos únicos permiten referencias eficientes
- Timestamps para auditoría y debugging

### Relaciones y Claves Foráneas

```python
# Tabla de rutas (relación muchos-a-muchos con estaciones)
cursor.execute("""
    CREATE TABLE IF NOT EXISTS routes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        origin_id INTEGER NOT NULL,              -- FK a stations
        destination_id INTEGER NOT NULL,         -- FK a stations
        train_number TEXT NOT NULL,              -- Número del tren
        train_type TEXT NOT NULL,                -- Tipo de tren
        departure_time TIMESTAMP NOT NULL,       -- Hora salida
        arrival_time TIMESTAMP NOT NULL,         -- Hora llegada
        duration_minutes INTEGER NOT NULL,       -- Duración calculada
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (origin_id) REFERENCES stations (id),     -- Integridad referencial
        FOREIGN KEY (destination_id) REFERENCES stations (id),
        UNIQUE(origin_id, destination_id, train_number, departure_time)  -- Evita duplicados
    )
""")
```

**Integridad Referencial**:
- FOREIGN KEY garantiza datos consistentes
- UNIQUE constraint previene duplicación
- Normalización reduce espacio de almacenamiento

### Índices para Rendimiento

```python
# Índices estratégicos para consultas frecuentes
cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_prices_route_date
    ON prices (route_id, travel_date)          -- Consultas por ruta y fecha
""")

cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_prices_scraped_at
    ON prices (scraped_at)                     -- Consultas temporales
""")
```

**¿Por qué estos índices?**
- `route_id, travel_date`: Consulta más común (precio para ruta específica)
- `scraped_at`: Para limpieza de datos antiguos
- Mejora significativa en performance de SELECT

### Context Manager para Conexiones

```python
@contextmanager
def get_connection(self):
    """Gestión automática de conexiones a la base de datos."""
    conn = sqlite3.connect(self.db_path)
    conn.row_factory = sqlite3.Row    # Permite acceso tipo diccionario: row['columna']
    try:
        yield conn                    # Devuelve la conexión
    finally:
        conn.close()                  # Cleanup automático
```

**Ventajas**:
- No hay leaks de conexión
- Manejo automático de excepciones
- Row factory para acceso más cómodo
- Patrón estándar de Python

### Operaciones CRUD

```python
def add_station(self, station: Station) -> int:
    """Añade estación o devuelve ID si ya existe (idempotente)."""
    with self.get_connection() as conn:
        cursor = conn.cursor()

        # Intentar obtener estación existente primero
        cursor.execute("SELECT id FROM stations WHERE code = ?", (station.code,))
        existing = cursor.fetchone()

        if existing:
            return existing['id']    # Devolver ID existente

        # Insertar nueva estación solo si no existe
        cursor.execute("""
            INSERT INTO stations (code, name, city) VALUES (?, ?, ?)
        """, (station.code, station.name, station.city))

        station_id = cursor.lastrowid    # ID de la nueva inserción
        conn.commit()                    # Confirmar transacción
        return station_id
```

**Operaciones Idempotentes**:
- Múltiples ejecuciones dan el mismo resultado
- Previene duplicación de datos
- Facilita reprocessing de datos

## 4. Optimización (`optimizer.py`)

### Análisis Estadístico

```python
def _analyze_price_trends(self, history: PriceHistory, current_price: Decimal) -> Dict[str, Any]:
    """Análisis estadístico completo de tendencias de precios."""

    prices = [p.price for p in history.prices]              # Extraer solo precios
    recent_prices = [p.price for p in history.prices[-7:]]  # Últimos 7 puntos

    analysis = {
        "historical_low": min(prices),                       # Mínimo histórico
        "historical_high": max(prices),                      # Máximo histórico
        "historical_average": mean(prices),                  # Media histórica
        "recent_average": mean(recent_prices),               # Media reciente
        "price_volatility": stdev(prices) if len(prices) > 1 else 0,  # Volatilidad
        "current_vs_historical_low": float(current_price / min(prices)),      # Ratio vs mínimo
        "current_vs_average": float(current_price / mean(prices)),            # Ratio vs media
        "trend": self._calculate_trend(recent_prices),       # Tendencia reciente
        "is_outlier": self._is_price_outlier(current_price, prices)           # Detección outliers
    }
    return analysis
```

**Métricas Clave**:
- **Volatilidad**: Desviación estándar indica variabilidad de precios
- **Ratios**: Comparación relativa más útil que diferencias absolutas
- **Tendencia**: Dirección del movimiento de precios
- **Outliers**: Precios anormalmente altos/bajos

### Algoritmo de Tendencias

```python
def _calculate_trend(self, prices: List[Decimal]) -> str:
    """Calcula la tendencia reciente de precios con umbral."""
    if len(prices) < 2:
        return "stable"

    # Cambio porcentual entre primer y último precio del período
    recent_change = (prices[-1] - prices[0]) / prices[0]

    if recent_change > 0.05:      # Incremento > 5%
        return "rising"
    elif recent_change < -0.05:   # Descenso > 5%
        return "falling"
    else:
        return "stable"           # Cambio menor al 5%
```

**¿Por qué 5% de umbral?**
- Filtra fluctuaciones menores ("ruido")
- Identifica cambios significativos
- Evita recomendaciones por variaciones mínimas

### Sistema de Recomendaciones

```python
def _generate_recommendation(self, current_price, days_until_departure, analysis, history):
    """Motor de decisión basado en múltiples factores."""

    factors = []  # Lista de factores considerados

    # Factor 1: Urgencia temporal
    if days_until_departure <= 3:
        factors.append(("urgent", 0.8, "Very close to departure"))
        recommendation = OptimizationRecommendation.BUY_NOW
    elif days_until_departure <= 7:
        factors.append(("soon", 0.6, "Close to departure"))

    # Factor 2: Calidad del precio
    if analysis["current_vs_historical_low"] <= 1.1:  # Dentro del 10% del mínimo histórico
        factors.append(("excellent_price", 0.9, "Excellent price"))
        recommendation = OptimizationRecommendation.BUY_NOW
    elif analysis["current_vs_average"] <= 0.9:       # 10% por debajo de la media
        factors.append(("good_price", 0.7, "Good price"))

    # Factor 3: Tendencia del mercado
    if analysis["trend"] == "falling":
        factors.append(("falling_trend", 0.6, "Prices are falling"))
        if recommendation != OptimizationRecommendation.BUY_NOW:
            recommendation = OptimizationRecommendation.WAIT

    # Calcular confianza como promedio de factores
    confidence = mean([factor[1] for factor in factors])

    return recommendation, confidence, factors
```

**Sistema Multi-Factor**:
- Combina urgencia temporal + calidad precio + tendencia
- Pesos diferentes según importancia del factor
- Explicación transparente del razonamiento

## 5. CLI (`cli.py`)

### Comando de Búsqueda

```python
@main.command()
@click.option("--origin", "-o", required=True, help="Origin station")
@click.option("--destination", "-d", required=True, help="Destination station")
@click.option("--date", "-dt", required=True, help="Travel date (YYYY-MM-DD)")
@click.option("--headless/--no-headless", default=True, help="Run browser in headless mode")
def search(origin: str, destination: str, date: str, headless: bool):
    """Busca rutas de tren disponibles."""

    # Validación y conversión de fecha
    try:
        travel_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        console.print("❌ Invalid date format. Use YYYY-MM-DD", style="red")
        return

    # Indicador visual de progreso
    with console.status("[bold green]Searching for trains..."):
        try:
            # Ejecución asíncrona en CLI síncrono
            routes = asyncio.run(quick_search(origin, destination, travel_date, headless))

            if not routes:
                console.print("❌ No routes found", style="red")
                return

            # Tabla formateada con Rich
            table = Table(title=f"Train Routes: {origin} → {destination} ({date})")
            table.add_column("Train", style="cyan", no_wrap=True)
            table.add_column("Departure", style="green")
            table.add_column("Arrival", style="green")
            table.add_column("Duration", style="yellow")
            table.add_column("Type", style="magenta")

            # Poblar tabla con datos
            for route in routes:
                duration_hours = route.duration_minutes // 60
                duration_mins = route.duration_minutes % 60
                duration_str = f"{duration_hours}h {duration_mins}m"

                table.add_row(
                    route.train_number,
                    route.departure_time.strftime("%H:%M"),
                    route.arrival_time.strftime("%H:%M"),
                    duration_str,
                    route.train_type.value
                )

            console.print(table)

        except Exception as e:
            console.print(f"❌ Error searching for routes: {e}", style="red")
```

**Elementos Clave del CLI**:
- **Click decorators**: Parseo automático de argumentos
- **Validación temprana**: Evita ejecución costosa con datos inválidos
- **Rich console**: Output formateado y coloreado
- **Manejo de errores**: Mensajes user-friendly
- **Progress indicators**: UX mejorada para operaciones largas

### Comando de Optimización

```python
@main.command()
@click.option("--price", "-p", type=float, required=True, help="Current price in euros")
def optimize(origin: str, destination: str, date: str, price: float):
    """Obtiene recomendación de optimización para un precio."""

    # Crear ruta dummy para el análisis (en uso real vendría del scraping)
    dummy_route = TrainRoute(
        origin=Station(code="ORIG", name=origin, city=origin),
        destination=Station(code="DEST", name=destination, city=destination),
        departure_time=datetime.combine(travel_date, datetime.min.time()),
        arrival_time=datetime.combine(travel_date, datetime.min.time()),
        train_type=TrainType.AVE,
        train_number="DEMO",
        duration_minutes=120
    )

    optimizer = PriceOptimizer()
    result = optimizer.get_optimization_recommendation(dummy_route, price)

    # Colores según tipo de recomendación
    color = {
        "BUY_NOW": "green",
        "WAIT": "yellow",
        "PRICE_ALERT": "cyan",
        "NO_DATA": "red"
    }.get(result.recommendation.value, "white")

    # Panel formateado con Rich
    panel = Panel(
        f"""[bold]Recommendation:[/bold] [{color}]{result.recommendation.value}[/{color}]
[bold]Confidence:[/bold] {result.confidence:.1%}
[bold]Reasoning:[/bold] {result.reasoning}
[bold]Suggested Action:[/bold] {result.suggested_action}

[bold]Details:[/bold]
• Days until departure: {result.days_until_departure}
• Price trend: {result.price_trend or 'Unknown'}
• Optimal window: {result.optimal_purchase_window or 'Unknown'}""",
        title=f"Price Optimization: €{price}",
        expand=False
    )

    console.print(panel)
```

**Rich UI Components**:
- **Panel**: Contenido enmarcado y titulado
- **Colores dinámicos**: Verde=comprar, Amarillo=esperar, etc.
- **Formato de porcentajes**: `:.1%` muestra 85.0%
- **Markup rich**: [bold], [green], etc. para estilizado

## Resumen de Patrones y Mejores Prácticas

### 1. **Manejo de Errores Robusto**
```python
try:
    # Operación que puede fallar
    result = await risky_operation()
except SpecificException as e:
    logger.error(f"Specific error: {e}")
    # Manejo específico
except Exception as e:
    logger.error(f"General error: {e}")
    # Fallback general
```

### 2. **Logging Estratégico**
```python
logger.info("Operation started")      # Puntos de control normales
logger.warning("Unexpected condition") # Situaciones anómalas no fatales
logger.error("Operation failed")      # Errores que requieren atención
```

### 3. **Validación de Datos**
```python
# Pydantic para validación automática
class Model(BaseModel):
    field: int = Field(..., ge=0, le=100)  # Entre 0 y 100

# Validación manual donde sea necesario
if not 0 <= value <= 100:
    raise ValueError("Value must be between 0 and 100")
```

### 4. **Operaciones Asíncronas**
```python
# Context managers async
async with resource:
    await async_operation()

# Gestión de timeouts
await asyncio.wait_for(operation(), timeout=30)
```

### 5. **Configuración Flexible**
```python
def __init__(self, param: str = "default", **kwargs):
    """Constructor con valores por defecto y extensibilidad."""
    self.param = param
    self.config = {**DEFAULT_CONFIG, **kwargs}
```

Este código implementa un sistema completo de scraping, análisis y optimización de precios con arquitectura modular, manejo robusto de errores, y una interfaz de usuario moderna.