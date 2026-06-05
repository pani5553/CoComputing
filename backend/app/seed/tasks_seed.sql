-- =============================================================================
-- Co-Computing — Seed de tareas representativas
-- Idempotente: INSERT ... ON CONFLICT DO NOTHING
-- Ejecutar con: python scripts/seed.py
-- =============================================================================

INSERT INTO tasks (id, title, task_type, description, reward, duration_min, duration_max,
                   difficulty, hardware_required, total_slots, slots_left, stages,
                   requester_name, status)
VALUES

-- 1. Entrenamiento ML — ResNet-50
(
    'a1000000-0000-0000-0000-000000000001',
    'Entrenamiento ML — ResNet-50 CIFAR-100',
    'entrenamiento_ml',
    'Entrenamiento completo de ResNet-50 sobre el dataset CIFAR-100 con 200 épocas. Requiere GPU con al menos 8 GB de VRAM. El modelo resultante se valida con el conjunto de test oficial.',
    5.00, 45, 90,
    'dificil', 'gpu',
    5, 5,
    ARRAY['Preparando entorno', 'Descargando dataset', 'Entrenando modelo', 'Validando precisión', 'Guardando checkpoints'],
    'AI Research Lab',
    'disponible'
),

-- 2. Renderizado 3D — Escena nocturna 4K
(
    'a1000000-0000-0000-0000-000000000002',
    'Renderizado de escena nocturna 4K',
    'renderizado_3d',
    'Renderizado fotorrealista de una escena urbana nocturna en 4K usando Blender Cycles. La escena incluye iluminación volumétrica, reflexiones y 2000 muestras por píxel.',
    8.50, 60, 120,
    'dificil', 'gpu',
    3, 3,
    ARRAY['Preparando entorno', 'Cargando escena 3D', 'Compilando shaders', 'Renderizando frames', 'Comprimiendo salida'],
    'VisualFX Studio',
    'disponible'
),

-- 3. Transcodificación de video — 4K a H.265
(
    'a1000000-0000-0000-0000-000000000003',
    'Transcodificación masiva 4K → H.265',
    'transcodificacion_video',
    'Batch de 50 archivos de video 4K en formato H.264 que deben ser convertidos a H.265 con compresión 2-pass. Requiere CPU potente para codificación por software.',
    3.25, 30, 60,
    'medio', 'cpu',
    8, 8,
    ARRAY['Preparando entorno', 'Analizando archivos', 'Codificando (pass 1)', 'Codificando (pass 2)', 'Verificando integridad'],
    'MediaStream Corp',
    'disponible'
),

-- 4. Análisis de datos — Big Data tweets
(
    'a1000000-0000-0000-0000-000000000004',
    'Análisis de sentimiento en dataset de tweets',
    'analisis_datos',
    'Procesamiento de 10 millones de tweets con análisis de sentimiento usando BERT multilingüe. Se requiere clasificar por polaridad y extraer entidades nombradas.',
    4.75, 40, 80,
    'medio', 'gpu',
    6, 6,
    ARRAY['Preparando entorno', 'Descargando dataset', 'Tokenizando textos', 'Inferencia con BERT', 'Agregando resultados'],
    'DataInsights Inc',
    'disponible'
),

-- 5. Simulación física — Dinámica de fluidos
(
    'a1000000-0000-0000-0000-000000000005',
    'Simulación de dinámica de fluidos CFD',
    'simulacion_fisica',
    'Simulación CFD de flujo turbulento en geometría de canal 3D usando el método Lattice-Boltzmann. Resolución de malla 512x512x256. Los resultados se exportan en formato VTK.',
    12.00, 90, 180,
    'dificil', 'mixto',
    2, 2,
    ARRAY['Preparando entorno', 'Generando malla', 'Inicializando solver', 'Iterando simulación', 'Exportando resultados VTK'],
    'CFD Solutions GmbH',
    'disponible'
),

-- 6. Entrenamiento ML — YOLOv8 detección de objetos
(
    'a1000000-0000-0000-0000-000000000006',
    'Fine-tuning YOLOv8 para detección industrial',
    'entrenamiento_ml',
    'Fine-tuning de YOLOv8x sobre dataset industrial de 50.000 imágenes con 25 clases de objetos. Incluye data augmentation y validación con mAP@0.5.',
    7.50, 60, 120,
    'dificil', 'gpu',
    4, 4,
    ARRAY['Preparando entorno', 'Cargando dataset', 'Aplicando augmentation', 'Entrenando modelo', 'Evaluando mAP'],
    'AutoVision Robotics',
    'disponible'
),

-- 7. Transcodificación — Audio a múltiples formatos
(
    'a1000000-0000-0000-0000-000000000007',
    'Conversión masiva de audio FLAC → MP3/AAC/OGG',
    'transcodificacion_video',
    'Conversión de 5000 archivos FLAC de alta resolución (24-bit/96kHz) a MP3 320kbps, AAC 256kbps y OGG 192kbps simultáneamente. Tarea paralelizable por CPU.',
    2.00, 20, 40,
    'facil', 'cpu',
    10, 10,
    ARRAY['Preparando entorno', 'Inventariando archivos', 'Convirtiendo a MP3', 'Convirtiendo a AAC/OGG', 'Verificando metadatos'],
    'SoundCloud Archive',
    'disponible'
),

-- 8. Análisis de datos — Genómica
(
    'a1000000-0000-0000-0000-000000000008',
    'Alineamiento de secuencias genómicas WGS',
    'analisis_datos',
    'Alineamiento de lecturas de secuenciación whole-genome (WGS) de 30x de cobertura contra el genoma de referencia hg38 usando BWA-MEM2. Requiere al menos 32 GB de RAM.',
    9.00, 70, 140,
    'dificil', 'mixto',
    3, 3,
    ARRAY['Preparando entorno', 'Descargando lecturas FASTQ', 'Indexando genoma referencia', 'Alineando secuencias', 'Generando fichero BAM/CRAM'],
    'GenomicsLab EU',
    'disponible'
),

-- 9. Renderizado 3D — Animación producto
(
    'a1000000-0000-0000-0000-000000000009',
    'Renderizado de animación publicitaria 360°',
    'renderizado_3d',
    'Secuencia de 240 frames de animación de producto de alta gama con rotación 360° y efectos de partículas. Resolución Full HD, 24fps, formato EXR.',
    6.00, 45, 90,
    'medio', 'gpu',
    5, 5,
    ARRAY['Preparando entorno', 'Cargando activos', 'Configurando iluminación', 'Renderizando secuencia', 'Componiendo frames EXR'],
    'BrandMotion Agency',
    'disponible'
),

-- 10. Simulación física — N-body astronomía
(
    'a1000000-0000-0000-0000-000000000010',
    'Simulación N-body de evolución galática',
    'simulacion_fisica',
    'Simulación gravitacional de 1 millón de partículas durante 10 Gyr de tiempo simulado usando el algoritmo Barnes-Hut. Los datos de salida se almacenan cada 100 Myr.',
    15.00, 120, 240,
    'dificil', 'gpu',
    2, 2,
    ARRAY['Preparando entorno', 'Generando condiciones iniciales', 'Inicializando árbol octree', 'Integrando trayectorias', 'Guardando snapshots'],
    'AstroSim Institute',
    'disponible'
),

-- 11. Análisis de datos — Logs de servidor
(
    'a1000000-0000-0000-0000-000000000011',
    'Análisis y anonimización de logs de acceso web',
    'analisis_datos',
    'Procesamiento de 500 GB de logs de acceso web en formato Apache/Nginx. Extracción de métricas de tráfico, detección de patrones anómalos y anonimización de IPs.',
    3.50, 25, 50,
    'facil', 'cpu',
    10, 10,
    ARRAY['Preparando entorno', 'Descomprimiendo logs', 'Parseando registros', 'Detectando anomalías', 'Generando informe'],
    'CloudOps Platform',
    'disponible'
),

-- 12. Transcodificación — Stream HLS
(
    'a1000000-0000-0000-0000-000000000012',
    'Generación de stream HLS adaptativo',
    'transcodificacion_video',
    'Transcodificación de contenido en vivo grabado (2 horas, 1080p) a HLS adaptativo con 5 perfiles de calidad: 240p, 360p, 480p, 720p, 1080p. Incluye segmentación y manifest.',
    4.00, 35, 70,
    'medio', 'mixto',
    7, 7,
    ARRAY['Preparando entorno', 'Analizando fuente', 'Generando perfiles de calidad', 'Segmentando HLS', 'Publicando manifest'],
    'StreamForce Media',
    'disponible'
),

-- 13. Entrenamiento ML — LLM fine-tuning
(
    'a1000000-0000-0000-0000-000000000013',
    'Fine-tuning LLM para soporte técnico en español',
    'entrenamiento_ml',
    'Fine-tuning de Mistral-7B con LoRA sobre 50.000 pares pregunta-respuesta de soporte técnico en español. Requiere GPU con 24 GB de VRAM mínimo.',
    18.00, 180, 360,
    'dificil', 'gpu',
    2, 2,
    ARRAY['Preparando entorno', 'Cargando modelo base', 'Preparando dataset', 'Entrenando con LoRA', 'Evaluando perplexity', 'Guardando adaptadores'],
    'TechSupport AI',
    'disponible'
),

-- 14. Simulación física — Crash test automoción
(
    'a1000000-0000-0000-0000-000000000014',
    'Simulación FEM de crash test frontal',
    'simulacion_fisica',
    'Análisis de elementos finitos de impacto frontal (56 km/h contra barrera deformable) para estructura de carrocería. Modelo de 2 millones de elementos con materiales elastoplásticos.',
    11.00, 80, 160,
    'dificil', 'mixto',
    3, 3,
    ARRAY['Preparando entorno', 'Cargando modelo FEM', 'Definiendo condiciones de contorno', 'Ejecutando solver implícito', 'Procesando deformaciones'],
    'AutoSafety Labs',
    'disponible'
),

-- 15. Análisis de datos — Imágenes satelitales
(
    'a1000000-0000-0000-0000-000000000015',
    'Clasificación de uso del suelo con Sentinel-2',
    'analisis_datos',
    'Clasificación supervisada de imágenes multiespectrales Sentinel-2 de España peninsular usando Random Forest y SVM. Generación de mapa de uso del suelo a 10m de resolución.',
    5.50, 40, 80,
    'medio', 'cpu',
    6, 6,
    ARRAY['Preparando entorno', 'Descargando tiles Sentinel-2', 'Preprocesando bandas', 'Entrenando clasificador', 'Generando mapa raster'],
    'GeoAnalytics Spain',
    'disponible'
),

-- 16. Renderizado 3D — Arquitectura interior
(
    'a1000000-0000-0000-0000-000000000016',
    'Visualización arquitectónica — Interior loft',
    'renderizado_3d',
    'Render fotorrealista de interior de loft de 200m² con luz natural. 5 vistas distintas en 4K. Material PBR, subsurface scattering en tejidos y caustics en cristal.',
    7.00, 50, 100,
    'medio', 'gpu',
    4, 4,
    ARRAY['Preparando entorno', 'Cargando modelo BIM', 'Configurando materiales PBR', 'Renderizando vistas', 'Post-procesando imágenes'],
    'ArchViz Consulting',
    'disponible'
),

-- 17. Transcodificación — Subtítulos y doblaje
(
    'a1000000-0000-0000-0000-000000000017',
    'Generación automática de subtítulos multiidioma',
    'transcodificacion_video',
    'Transcripción y traducción automática de 20 horas de contenido audiovisual a 8 idiomas usando Whisper large-v3. Incluye burn-in de subtítulos en formato SRT y ASS.',
    2.75, 20, 45,
    'facil', 'gpu',
    8, 8,
    ARRAY['Preparando entorno', 'Extrayendo audio', 'Transcribiendo con Whisper', 'Traduciendo a 8 idiomas', 'Generando ficheros SRT/ASS'],
    'GlobalContent Hub',
    'disponible'
),

-- 18. Análisis de datos — Fraude financiero
(
    'a1000000-0000-0000-0000-000000000018',
    'Detección de anomalías en transacciones financieras',
    'analisis_datos',
    'Entrenamiento de modelo de detección de fraude sobre dataset de 100M de transacciones usando Isolation Forest y Autoencoder. Dataset anonimizado y normalizado.',
    6.25, 50, 100,
    'dificil', 'gpu',
    4, 4,
    ARRAY['Preparando entorno', 'Cargando y validando dataset', 'Preprocesando transacciones', 'Entrenando modelos de anomalía', 'Evaluando métricas AUC-ROC'],
    'FinSecure Analytics',
    'disponible'
)

ON CONFLICT (id) DO NOTHING;
