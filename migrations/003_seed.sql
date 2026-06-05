-- =============================================================================
-- Co-Computing — Migration 003: Seed de producción
-- PostgreSQL 15 (Supabase)
-- Ejecutar DESPUÉS de 001_schema.sql y 002_rls.sql
-- Idempotente: usa INSERT ... ON CONFLICT DO NOTHING con UUIDs fijos
-- =============================================================================
--
-- CONTENIDO:
--   - 1 proveedor demo (email: demo@co-computing.io, password: demo1234)
--   - 1 wallet para el proveedor demo
--   - 3 transacciones de muestra para el proveedor demo
--   - 18 tareas variadas con stages[] realistas (status='disponible')
--
-- NOTA SOBRE EL HASH:
--   El hash de "demo1234" generado con bcrypt rounds=12:
--   $2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/lewdBpj8GFg0JkDK2
--   Compatible con passlib.hash.bcrypt (Python) y bcryptjs (Node.js).
-- =============================================================================

BEGIN;

-- =============================================================================
-- PROVEEDOR DEMO
-- UUID fijo para reproducibilidad en tests y desarrollo
-- =============================================================================
INSERT INTO providers (
    id,
    email,
    full_name,
    password_hash,
    trust_score,
    rank,
    tasks_completed,
    success_rate,
    total_earned,
    completion_rate,
    accuracy,
    response_time_score,
    client_rating,
    cpu_model,
    gpu_model,
    ram_gb,
    storage_gb,
    is_online,
    created_at,
    updated_at
) VALUES (
    '11111111-1111-1111-1111-111111111111',
    'demo@co-computing.io',
    'Demo Provider',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/lewdBpj8GFg0JkDK2',
    -- trust_score = 87*0.40 + 85*0.30 + 75*0.20 + 70*0.10
    --            = 34.80 + 25.50 + 15.00 + 7.00 = 82.30
    82.30,
    'experto',
    12,
    -- success_rate = 12 completadas / (12+2 total) * 100 = 85.71
    85.71,
    -- total_earned = suma de las transacciones pago_tarea del seed
    38.50,
    -- completion_rate: usada en trust_score
    87.00,
    85.00,
    75.00,
    70.00,
    'AMD Ryzen 9 5950X',
    'NVIDIA GeForce RTX 3080',
    32,
    1000,
    false,
    '2026-01-15T10:00:00Z',
    '2026-06-04T18:30:00Z'
)
ON CONFLICT (id) DO NOTHING;

-- =============================================================================
-- WALLET DEL PROVEEDOR DEMO
-- =============================================================================
INSERT INTO wallets (
    id,
    provider_id,
    available_balance,
    pending_balance,
    total_earned,
    total_withdrawn,
    created_at,
    updated_at
) VALUES (
    '22222222-2222-2222-2222-222222222222',
    '11111111-1111-1111-1111-111111111111',
    -- available_balance = total_earned - total_withdrawn = 38.50 - 20.00 = 18.50
    18.50,
    0.00,
    38.50,
    20.00,
    '2026-01-15T10:00:00Z',
    '2026-06-04T18:30:00Z'
)
ON CONFLICT (id) DO NOTHING;

-- =============================================================================
-- TRANSACCIONES DE MUESTRA DEL PROVEEDOR DEMO
-- =============================================================================
INSERT INTO transactions (
    id,
    provider_id,
    task_id,
    amount,
    tx_type,
    status,
    description,
    withdraw_method,
    withdraw_destination,
    created_at
) VALUES
(
    '33333333-3333-3333-3333-333333333301',
    '11111111-1111-1111-1111-111111111111',
    NULL,
    5.50,
    'pago_tarea',
    'completada',
    'Recompensa por tarea completada: Renderizado de escena arquitectónica 4K',
    NULL,
    NULL,
    '2026-05-20T14:30:00Z'
),
(
    '33333333-3333-3333-3333-333333333302',
    '11111111-1111-1111-1111-111111111111',
    NULL,
    20.00,
    'retiro',
    'completada',
    'Retiro via PayPal procesado',
    'paypal',
    'demo@paypal.com',
    '2026-05-25T09:00:00Z'
),
(
    '33333333-3333-3333-3333-333333333303',
    '11111111-1111-1111-1111-111111111111',
    NULL,
    3.00,
    'bonus',
    'completada',
    'Bonus de bienvenida por completar las primeras 10 tareas',
    NULL,
    NULL,
    '2026-06-01T12:00:00Z'
)
ON CONFLICT (id) DO NOTHING;

-- =============================================================================
-- TAREAS — 18 tareas variadas con stages[] realistas
-- UUIDs fijos para reproducibilidad. status='disponible', slots_left > 0.
-- =============================================================================

-- ─── RENDERIZADO 3D ──────────────────────────────────────────────────────────

INSERT INTO tasks (
    id, title, task_type, description, reward,
    duration_min, duration_max, difficulty, hardware_required,
    total_slots, slots_left, stages, requester_name, requester_company, status
) VALUES (
    'aaaaaaaa-0001-0001-0001-000000000001',
    'Renderizado de escena arquitectónica 4K',
    'renderizado_3d',
    'Renderizado fotorrealista de un interior residencial de lujo utilizando Blender Cycles con 2048 muestras. La escena incluye iluminación HDRI, materiales PBR y geometría compleja. El resultado final debe ser una imagen 4K (3840x2160px) en formato EXR sin pérdida.',
    5.50,
    45, 90,
    'medio',
    'gpu',
    8, 8,
    ARRAY[
        'Cargando escena y activos',
        'Compilando shaders GPU',
        'Calentando muestras (warm-up)',
        'Renderizando tiles',
        'Aplicando denoising',
        'Exportando imagen EXR'
    ],
    'Studio Arq Visual',
    'Arq Visual S.L.',
    'disponible'
) ON CONFLICT (id) DO NOTHING;

INSERT INTO tasks (
    id, title, task_type, description, reward,
    duration_min, duration_max, difficulty, hardware_required,
    total_slots, slots_left, stages, requester_name, requester_company, status
) VALUES (
    'aaaaaaaa-0001-0001-0001-000000000002',
    'Animación de personaje 3D — secuencia de 300 frames',
    'renderizado_3d',
    'Renderizado de una secuencia de 300 fotogramas de un personaje animado en alta calidad. El personaje cuenta con rig completo, ropa simulada y subsurface scattering en piel. Resolución 1920x1080, 24fps, formato PNG secuencia.',
    12.00,
    90, 180,
    'dificil',
    'gpu',
    5, 5,
    ARRAY[
        'Cargando rig y animaciones',
        'Simulando física de ropa',
        'Preparando caché de simulación',
        'Renderizando secuencia de frames',
        'Compilando secuencia PNG',
        'Verificando fotogramas faltantes'
    ],
    'Pixel Motion Studio',
    'Pixel Motion S.L.',
    'disponible'
) ON CONFLICT (id) DO NOTHING;

INSERT INTO tasks (
    id, title, task_type, description, reward,
    duration_min, duration_max, difficulty, hardware_required,
    total_slots, slots_left, stages, requester_name, requester_company, status
) VALUES (
    'aaaaaaaa-0001-0001-0001-000000000003',
    'Renderizado de producto para e-commerce — pack 6 vistas',
    'renderizado_3d',
    'Renderizado de producto industrial (auriculares gaming) desde 6 ángulos distintos sobre fondo blanco y negro. Iluminación de estudio, reflexiones controladas y 512 muestras por imagen. Resolución 2048x2048px en PNG con canal alfa.',
    3.00,
    15, 30,
    'facil',
    'gpu',
    10, 10,
    ARRAY[
        'Importando modelo 3D del producto',
        'Configurando luces de estudio',
        'Renderizando 6 vistas',
        'Post-procesado de canales alfa',
        'Exportando PNGs finales'
    ],
    'TechGear Marketing',
    NULL,
    'disponible'
) ON CONFLICT (id) DO NOTHING;

-- ─── ENTRENAMIENTO ML ─────────────────────────────────────────────────────────

INSERT INTO tasks (
    id, title, task_type, description, reward,
    duration_min, duration_max, difficulty, hardware_required,
    total_slots, slots_left, stages, requester_name, requester_company, status
) VALUES (
    'aaaaaaaa-0001-0001-0001-000000000004',
    'Entrenamiento ResNet-50 sobre CIFAR-100 — 200 épocas',
    'entrenamiento_ml',
    'Entrenamiento completo de ResNet-50 con PyTorch sobre el dataset CIFAR-100 durante 200 épocas. Optimizador SGD con momentum 0.9, lr=0.1 con scheduler cosine annealing. Se espera alcanzar al menos 75% de top-1 accuracy en el set de validación.',
    8.00,
    60, 120,
    'dificil',
    'gpu',
    4, 4,
    ARRAY[
        'Descargando dataset CIFAR-100',
        'Inicializando arquitectura ResNet-50',
        'Ejecutando épocas de entrenamiento',
        'Evaluando en set de validación',
        'Guardando checkpoints del modelo',
        'Exportando métricas finales'
    ],
    'AI Research Lab',
    'Deep Learning Institute',
    'disponible'
) ON CONFLICT (id) DO NOTHING;

INSERT INTO tasks (
    id, title, task_type, description, reward,
    duration_min, duration_max, difficulty, hardware_required,
    total_slots, slots_left, stages, requester_name, requester_company, status
) VALUES (
    'aaaaaaaa-0001-0001-0001-000000000005',
    'Fine-tuning BERT para clasificación de sentimientos',
    'entrenamiento_ml',
    'Fine-tuning de BERT-base-uncased sobre un dataset de reseñas de productos en español (50.000 ejemplos). Clasificación binaria (positivo/negativo). Entrenamiento por 3 épocas con AdamW lr=2e-5. Guardar modelo en formato HuggingFace.',
    6.50,
    40, 80,
    'dificil',
    'gpu',
    3, 3,
    ARRAY[
        'Descargando modelo BERT preentrenado',
        'Preparando y tokenizando dataset',
        'Fine-tuning épocas 1-3',
        'Evaluando F1-score en test',
        'Guardando modelo HuggingFace',
        'Generando reporte de métricas'
    ],
    'NLP Solutions',
    'NLP Solutions S.A.',
    'disponible'
) ON CONFLICT (id) DO NOTHING;

INSERT INTO tasks (
    id, title, task_type, description, reward,
    duration_min, duration_max, difficulty, hardware_required,
    total_slots, slots_left, stages, requester_name, requester_company, status
) VALUES (
    'aaaaaaaa-0001-0001-0001-000000000006',
    'Entrenamiento de árbol de decisión para detección de fraude',
    'entrenamiento_ml',
    'Entrenamiento de un modelo XGBoost para detección de transacciones fraudulentas sobre un dataset de 500.000 registros (features anonimizadas). Optimización de hiperparámetros con Optuna (50 trials). Exportar modelo en formato ONNX.',
    2.50,
    20, 45,
    'facil',
    'cpu',
    12, 12,
    ARRAY[
        'Cargando y validando dataset',
        'Ingeniería de features',
        'Búsqueda de hiperparámetros (Optuna)',
        'Entrenando modelo XGBoost final',
        'Evaluando AUC-ROC en test',
        'Exportando modelo ONNX'
    ],
    'FinTech Analytics',
    NULL,
    'disponible'
) ON CONFLICT (id) DO NOTHING;

-- ─── TRANSCODIFICACIÓN DE VÍDEO ───────────────────────────────────────────────

INSERT INTO tasks (
    id, title, task_type, description, reward,
    duration_min, duration_max, difficulty, hardware_required,
    total_slots, slots_left, stages, requester_name, requester_company, status
) VALUES (
    'aaaaaaaa-0001-0001-0001-000000000007',
    'Transcodificación de cortometraje 4K a múltiples formatos',
    'transcodificacion_video',
    'Transcodificación de un cortometraje de 12 minutos en 4K RAW (ProRes 4444, 180GB) a tres formatos de distribución: H.264 1080p para web (CRF 18), H.265 4K para streaming (CRF 22) y VP9 1080p para YouTube. Audio AAC 192kbps.',
    4.50,
    30, 60,
    'medio',
    'cpu',
    6, 6,
    ARRAY[
        'Verificando integridad del archivo fuente',
        'Extrayendo pistas de audio',
        'Transcodificando a H.264 1080p',
        'Transcodificando a H.265 4K',
        'Transcodificando a VP9 1080p',
        'Multiplexando audio y verificando salida'
    ],
    'Indie Film Productions',
    'IFP Media',
    'disponible'
) ON CONFLICT (id) DO NOTHING;

INSERT INTO tasks (
    id, title, task_type, description, reward,
    duration_min, duration_max, difficulty, hardware_required,
    total_slots, slots_left, stages, requester_name, requester_company, status
) VALUES (
    'aaaaaaaa-0001-0001-0001-000000000008',
    'Conversión de archivo de vídeo a H.265 con aceleración GPU',
    'transcodificacion_video',
    'Transcodificación rápida de un vídeo FHD (AVI DivX, 45 minutos, 8GB) a H.265/HEVC usando NVENC para máxima velocidad. CRF 20, preset slow. Audio copiado sin recodificar. Salida en contenedor MKV.',
    1.80,
    10, 20,
    'facil',
    'gpu',
    15, 15,
    ARRAY[
        'Analizando stream de vídeo fuente',
        'Inicializando encoder NVENC H.265',
        'Transcodificando vídeo (NVENC)',
        'Copiando stream de audio',
        'Multiplexando en contenedor MKV',
        'Verificando duración y reproducción'
    ],
    'VideoTools Pro',
    NULL,
    'disponible'
) ON CONFLICT (id) DO NOTHING;

INSERT INTO tasks (
    id, title, task_type, description, reward,
    duration_min, duration_max, difficulty, hardware_required,
    total_slots, slots_left, stages, requester_name, requester_company, status
) VALUES (
    'aaaaaaaa-0001-0001-0001-000000000009',
    'Proceso de vídeo multicanal para plataforma OTT — 8 resoluciones',
    'transcodificacion_video',
    'Generación de un ladder de transcodificación completo (ABR) para una serie de TV: 240p, 360p, 480p, 720p, 1080p, 1440p, 2160p y thumbnail sprite. Formato HLS con segmentos de 6 segundos. Clave de cifrado AES-128 proporcionada. Duración del episodio: 45 minutos.',
    18.00,
    120, 240,
    'dificil',
    'mixto',
    2, 2,
    ARRAY[
        'Validando fuente y clave de cifrado',
        'Generando representaciones 240p-720p',
        'Generando representaciones 1080p-2160p',
        'Creando sprite de thumbnails',
        'Segmentando en chunks HLS',
        'Aplicando cifrado AES-128',
        'Generando manifiestos m3u8'
    ],
    'StreamFlow OTT',
    'StreamFlow Technologies S.A.',
    'disponible'
) ON CONFLICT (id) DO NOTHING;

-- ─── ANÁLISIS DE DATOS ────────────────────────────────────────────────────────

INSERT INTO tasks (
    id, title, task_type, description, reward,
    duration_min, duration_max, difficulty, hardware_required,
    total_slots, slots_left, stages, requester_name, requester_company, status
) VALUES (
    'aaaaaaaa-0001-0001-0001-000000000010',
    'Análisis de correlaciones en dataset genómico — 10M variantes',
    'analisis_datos',
    'Cálculo de correlaciones de Pearson y Spearman entre 10 millones de variantes SNP y 120 fenotipos clínicos usando pandas/numpy. Los datos están en formato VCF comprimido (12GB). Se requiere paralelización con joblib y exportación de la matriz de correlaciones en formato HDF5.',
    9.00,
    60, 120,
    'dificil',
    'cpu',
    3, 3,
    ARRAY[
        'Descomprimiendo y parseando VCF',
        'Normalizando variantes y fenotipos',
        'Calculando correlaciones Pearson',
        'Calculando correlaciones Spearman',
        'Filtrando resultados significativos (p<0.05)',
        'Exportando matriz HDF5'
    ],
    'BioData Research',
    'BioData Research Institute',
    'disponible'
) ON CONFLICT (id) DO NOTHING;

INSERT INTO tasks (
    id, title, task_type, description, reward,
    duration_min, duration_max, difficulty, hardware_required,
    total_slots, slots_left, stages, requester_name, requester_company, status
) VALUES (
    'aaaaaaaa-0001-0001-0001-000000000011',
    'Procesamiento de logs de servidor web — 500M líneas',
    'analisis_datos',
    'Parsing y análisis estadístico de 500 millones de líneas de acceso Apache/Nginx (formato Combined Log). Extracción de métricas: top 100 IPs, distribución de status codes, latencia p50/p95/p99 por endpoint, picos de tráfico por hora. Salida en JSON y CSV.',
    3.50,
    25, 50,
    'medio',
    'cpu',
    8, 8,
    ARRAY[
        'Contando y validando líneas de log',
        'Parseando campos de acceso',
        'Agregando métricas por IP y endpoint',
        'Calculando percentiles de latencia',
        'Detectando picos de tráfico',
        'Exportando resultados JSON/CSV'
    ],
    'WebOps Analytics',
    NULL,
    'disponible'
) ON CONFLICT (id) DO NOTHING;

INSERT INTO tasks (
    id, title, task_type, description, reward,
    duration_min, duration_max, difficulty, hardware_required,
    total_slots, slots_left, stages, requester_name, requester_company, status
) VALUES (
    'aaaaaaaa-0001-0001-0001-000000000012',
    'Cálculo de estadísticas descriptivas sobre CSV de ventas',
    'analisis_datos',
    'Análisis estadístico básico de un dataset de ventas minoristas (CSV, 2M filas, 18 columnas). Calcular media, mediana, desviación estándar, percentiles y distribución por categoría de producto, región y trimestre. Generar informe HTML con gráficos Matplotlib.',
    1.50,
    8, 15,
    'facil',
    'cpu',
    20, 20,
    ARRAY[
        'Cargando y validando CSV',
        'Calculando estadísticas descriptivas',
        'Agrupando por categoría y región',
        'Generando gráficos Matplotlib',
        'Exportando informe HTML'
    ],
    'Retail Insights Co.',
    NULL,
    'disponible'
) ON CONFLICT (id) DO NOTHING;

-- ─── SIMULACIÓN FÍSICA ────────────────────────────────────────────────────────

INSERT INTO tasks (
    id, title, task_type, description, reward,
    duration_min, duration_max, difficulty, hardware_required,
    total_slots, slots_left, stages, requester_name, requester_company, status
) VALUES (
    'aaaaaaaa-0001-0001-0001-000000000013',
    'Simulación CFD de flujo en conducto bifurcado — 10M celdas',
    'simulacion_fisica',
    'Simulación de dinámica de fluidos computacional (OpenFOAM) de flujo laminar en un conducto con bifurcación en Y. Malla estructurada de 10 millones de celdas. Reynolds 2300. Solver simpleFOAM con 5000 iteraciones. Exportar campos de velocidad y presión en VTK.',
    15.00,
    120, 240,
    'dificil',
    'cpu',
    2, 2,
    ARRAY[
        'Cargando malla CFD y condiciones de contorno',
        'Inicializando campos de velocidad/presión',
        'Ejecutando solver simpleFOAM (iter 1-2500)',
        'Ejecutando solver simpleFOAM (iter 2500-5000)',
        'Comprobando convergencia de residuos',
        'Exportando campos VTK'
    ],
    'CFD Engineering',
    'CFD Engineering Group S.L.',
    'disponible'
) ON CONFLICT (id) DO NOTHING;

INSERT INTO tasks (
    id, title, task_type, description, reward,
    duration_min, duration_max, difficulty, hardware_required,
    total_slots, slots_left, stages, requester_name, requester_company, status
) VALUES (
    'aaaaaaaa-0001-0001-0001-000000000014',
    'Simulación de colisión de vehículo — análisis de elementos finitos',
    'simulacion_fisica',
    'Simulación de impacto frontal de vehículo a 56 km/h contra barrera rígida (NCAP) con LS-DYNA. Modelo de 1.2 millones de elementos. Duración del evento: 120 ms. Análisis de deformación de la zona de crumple, fuerzas sobre el maniquí Hybrid III y energía absorbida.',
    22.00,
    180, 360,
    'dificil',
    'mixto',
    1, 1,
    ARRAY[
        'Cargando modelo FEM y materiales',
        'Verificando condiciones de contacto',
        'Ejecutando simulación dinámica explícita',
        'Extrayendo curvas de fuerza-desplazamiento',
        'Calculando energía absorbida por zona',
        'Generando animación VTK y reporte'
    ],
    'AutoSim Research',
    'AutoSim Engineering Ltd.',
    'disponible'
) ON CONFLICT (id) DO NOTHING;

INSERT INTO tasks (
    id, title, task_type, description, reward,
    duration_min, duration_max, difficulty, hardware_required,
    total_slots, slots_left, stages, requester_name, requester_company, status
) VALUES (
    'aaaaaaaa-0001-0001-0001-000000000015',
    'Simulación de partículas N-cuerpo — sistema estelar 100k estrellas',
    'simulacion_fisica',
    'Simulación gravitacional N-cuerpo de un sistema estelar de 100.000 partículas usando Barnes-Hut con theta=0.5. Integración leapfrog de 10.000 pasos de tiempo. Exportar posiciones y velocidades cada 100 pasos en formato HDF5 para visualización posterior.',
    7.50,
    45, 90,
    'medio',
    'cpu',
    5, 5,
    ARRAY[
        'Inicializando distribución de partículas',
        'Construyendo árbol octree inicial',
        'Ejecutando pasos de tiempo 1-5000',
        'Ejecutando pasos de tiempo 5001-10000',
        'Exportando snapshots HDF5',
        'Calculando energía total y verificando conservación'
    ],
    'Astro Computational Lab',
    'Universidad Computacional',
    'disponible'
) ON CONFLICT (id) DO NOTHING;

-- ─── TAREAS ADICIONALES (dificultad facil/media, variedad de HW y recompensas) ──

INSERT INTO tasks (
    id, title, task_type, description, reward,
    duration_min, duration_max, difficulty, hardware_required,
    total_slots, slots_left, stages, requester_name, requester_company, status
) VALUES (
    'aaaaaaaa-0001-0001-0001-000000000016',
    'Upscaling de imágenes con Real-ESRGAN — lote de 500 imágenes',
    'entrenamiento_ml',
    'Aplicar el modelo Real-ESRGAN x4plus sobre un lote de 500 imágenes JPEG (resolución promedio 640x480px). Escalar a 2560x1920px usando inferencia GPU. Guardar resultados en PNG sin pérdida. El modelo preentrenado se descargará automáticamente desde el repositorio oficial.',
    4.00,
    20, 40,
    'facil',
    'gpu',
    10, 10,
    ARRAY[
        'Descargando modelo Real-ESRGAN preentrenado',
        'Cargando lote de imágenes fuente',
        'Aplicando upscaling x4 (GPU inference)',
        'Guardando imágenes PNG de salida',
        'Verificando dimensiones y calidad'
    ],
    'PhotoEnhance Studio',
    NULL,
    'disponible'
) ON CONFLICT (id) DO NOTHING;

INSERT INTO tasks (
    id, title, task_type, description, reward,
    duration_min, duration_max, difficulty, hardware_required,
    total_slots, slots_left, stages, requester_name, requester_company, status
) VALUES (
    'aaaaaaaa-0001-0001-0001-000000000017',
    'Compresión y deduplicación de backup — dataset 50GB',
    'analisis_datos',
    'Análisis de duplicados y compresión optimizada de un directorio de backups de 50GB (mix de imágenes RAW, documentos PDF y vídeos). Usar hash SHA-256 para deduplicación, zstd nivel 19 para compresión. Generar informe de ahorro de espacio y árbol de duplicados.',
    2.00,
    15, 30,
    'facil',
    'cpu',
    18, 18,
    ARRAY[
        'Indexando archivos y calculando hashes SHA-256',
        'Identificando grupos de duplicados',
        'Comprimiendo archivos únicos con zstd-19',
        'Generando árbol de duplicados eliminados',
        'Exportando informe de ahorro de espacio'
    ],
    'BackupOps',
    NULL,
    'disponible'
) ON CONFLICT (id) DO NOTHING;

INSERT INTO tasks (
    id, title, task_type, description, reward,
    duration_min, duration_max, difficulty, hardware_required,
    total_slots, slots_left, stages, requester_name, requester_company, status
) VALUES (
    'aaaaaaaa-0001-0001-0001-000000000018',
    'Renderizado de visualización científica — campo de temperatura 3D',
    'renderizado_3d',
    'Visualización volumétrica de un campo escalar de temperatura 3D (256x256x256 voxels) usando VTK y ParaView en modo batch. Generar 360 imágenes de rotación orbital (1920x1080) y compilarlas en un vídeo MP4 H.264 a 30fps. Paleta de color viridis con escala logarítmica.',
    6.00,
    40, 80,
    'medio',
    'mixto',
    6, 6,
    ARRAY[
        'Cargando campo escalar VTK',
        'Configurando volumen y paleta de color',
        'Renderizando 360 frames de rotación orbital',
        'Compilando secuencia de frames en MP4',
        'Verificando duración y calidad del vídeo'
    ],
    'SciViz Lab',
    'Instituto Nacional de Simulación',
    'disponible'
) ON CONFLICT (id) DO NOTHING;

COMMIT;

-- =============================================================================
-- VERIFICACIÓN POST-SEED (consultas informativas)
-- =============================================================================
-- SELECT COUNT(*) AS total_tasks FROM tasks WHERE status = 'disponible';
-- -- Esperado: 18
--
-- SELECT id, email, trust_score, rank, tasks_completed FROM providers;
-- -- Esperado: 1 fila (demo@co-computing.io)
--
-- SELECT provider_id, available_balance, total_earned, total_withdrawn FROM wallets;
-- -- Esperado: 1 fila (18.50 disponible, 38.50 ganado, 20.00 retirado)
--
-- SELECT tx_type, status, amount FROM transactions ORDER BY created_at;
-- -- Esperado: 3 filas (pago_tarea, retiro, bonus)
--
-- SELECT task_type, difficulty, hardware_required, reward
-- FROM tasks
-- ORDER BY reward DESC;
-- -- Esperado: 18 filas ordenadas por recompensa descendente
-- =============================================================================
