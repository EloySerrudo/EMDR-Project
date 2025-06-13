-- administradores
CREATE TABLE IF NOT EXISTS administradores (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    user TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
);

-- terapeutas
CREATE TABLE IF NOT EXISTS terapeutas (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    user TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    apellido_paterno TEXT NOT NULL,
    apellido_materno TEXT,
    nombre TEXT NOT NULL,
    genero INTEGER NOT NULL CHECK (genero IN (0, 1))
);

-- pacientes
CREATE TABLE IF NOT EXISTS pacientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    apellido_paterno TEXT NOT NULL,
    apellido_materno TEXT,
    nombre TEXT NOT NULL,
    fecha_nacimiento DATE NOT NULL,
    celular TEXT NOT NULL,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    comentarios TEXT
);

-- diagnósticos
CREATE TABLE IF NOT EXISTS diagnosticos (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    id_paciente INTEGER NOT NULL,
    codigo_diagnostico TEXT NOT NULL,  -- Ej: F41.1 (CIE-10)
    nombre_diagnostico TEXT NOT NULL,  -- Ej: "Trastorno de ansiedad generalizada"
    fecha_diagnostico DATE NOT NULL,
    fecha_resolucion DATE,  -- NULL si aún está activo
    estado TEXT DEFAULT 'activo' CHECK (estado IN ('activo', 'resuelto', 'en_remision')),
    id_terapeuta INTEGER,
    comentarios TEXT,
    FOREIGN KEY (id_paciente) REFERENCES pacientes(id),
    FOREIGN KEY (id_terapeuta) REFERENCES terapeutas(id)
);

-- sesiones
CREATE TABLE IF NOT EXISTS sesiones (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    id_paciente INTEGER NOT NULL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    datos_ms BLOB,
    datos_eog BLOB,
    datos_ppg BLOB,
    datos_bpm BLOB,
    comentarios TEXT,
    FOREIGN KEY (id_paciente) REFERENCES pacientes(id)
);