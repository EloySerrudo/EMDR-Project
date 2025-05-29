-- administradores
CREATE TABLE IF NOT EXISTS administradores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
);

-- terapeutas
CREATE TABLE IF NOT EXISTS terapeutas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    apellido_paterno TEXT NOT NULL,
    apellido_materno TEXT NOT NULL,
    nombre TEXT NOT NULL
);

-- pacientes
CREATE TABLE IF NOT EXISTS pacientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    apellido_paterno TEXT NOT NULL,
    apellido_materno TEXT NOT NULL,
    nombre TEXT NOT NULL,
    edad INTEGER,
    celular TEXT NOT NULL,
    notas TEXT
);

-- sesiones
CREATE TABLE IF NOT EXISTS sesiones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_paciente INTEGER,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    datos_eog BLOB,
    datos_ppg BLOB,
    datos_bpm BLOB,
    notas TEXT,
    FOREIGN KEY (id_paciente) REFERENCES pacientes(id)
);