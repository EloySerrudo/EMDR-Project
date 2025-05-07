-- terapeutas
CREATE TABLE IF NOT EXISTS terapeutas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT UNIQUE NOT NULL,
    contraseña TEXT NOT NULL
);

-- pacientes
CREATE TABLE IF NOT EXISTS pacientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    edad INTEGER,
    notas TEXT
);

-- sesiones
CREATE TABLE IF NOT EXISTS sesiones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_paciente INTEGER,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    datos_eog BLOB,
    datos_ppg BLOB,
    notas TEXT,
    FOREIGN KEY (id_paciente) REFERENCES pacientes(id)
);