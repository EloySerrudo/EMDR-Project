# Cargar librerías necesarias
library(readr)
library(dplyr)
library(ggplot2)
library(gridExtra)
library(corrr)
library(broom)
library(scales)

# Leer datos
csv_file <- "D:/Documentos/Projects/Python/EMDR-Project/src/pipeline/combined_heart_rate_data.csv"
combined_df <- read_csv(csv_file)

# Extraer datos
sensor_bpm <- combined_df$sensor_ppg_bpm
watch_bpm <- combined_df$samsung_watch_bpm

# === ANÁLISIS DE CORRELACIÓN ===
cat("=== ANÁLISIS DE CORRELACIÓN ===\n")

# Correlación de Pearson
pearson_test <- cor.test(sensor_bpm, watch_bpm, method = "pearson")
pearson_r <- pearson_test$estimate
pearson_p <- pearson_test$p.value

cat(sprintf("Correlación de Pearson: r = %.4f (p = %.4f)\n", pearson_r, pearson_p))

# Coeficiente de determinación
r_squared <- pearson_r^2
cat(sprintf("Coeficiente de determinación (R²): %.4f\n", r_squared))

# === MÉTRICAS DE ERROR ===
cat("\n=== MÉTRICAS DE ERROR ===\n")

# Error Cuadrático Medio (RMSE)
rmse <- sqrt(mean((watch_bpm - sensor_bpm)^2))
cat(sprintf("Error Cuadrático Medio (RMSE): %.2f BPM\n", rmse))

# === CREAR GRÁFICAS ELEGANTES ===

# Tema personalizado elegante
elegant_theme <- theme_minimal() +
  theme(
    panel.grid.major = element_line(color = "grey90", size = 0.5),
    panel.grid.minor = element_line(color = "grey95", size = 0.3),
    plot.title = element_text(size = 14, face = "bold", hjust = 0.5, color = "grey20"),
    plot.subtitle = element_text(size = 12, hjust = 0.5, color = "grey40"),
    axis.title = element_text(size = 12, face = "bold", color = "grey30"),
    axis.text = element_text(size = 10, color = "grey50"),
    legend.title = element_text(size = 11, face = "bold", color = "grey30"),
    legend.text = element_text(size = 10, color = "grey50"),
    legend.position = "bottom",
    plot.background = element_rect(fill = "white", color = NA),
    panel.background = element_rect(fill = "white", color = NA),
    strip.text = element_text(size = 11, face = "bold", color = "grey30")
  )

# 1. Diagrama de dispersión elegante
scatter_plot <- ggplot(combined_df, aes(x = sensor_ppg_bpm, y = samsung_watch_bpm)) +
  geom_point(alpha = 0.7, size = 3, color = "#2E86AB", stroke = 0.5) +
  geom_smooth(method = "lm", se = TRUE, color = "#E63946", fill = "#E63946", alpha = 0.2) +
  geom_abline(slope = 1, intercept = 0, linetype = "dashed", color = "#06D6A0", size = 1, alpha = 0.8) +
  labs(
    title = sprintf("Correlación entre Sensores"),
    subtitle = sprintf("Pearson = %.3f, R² = %.3f", pearson_r, r_squared),
    x = "Sensor PPG (BPM)",
    y = "Samsung Watch 6 (BPM)"
  ) +
  elegant_theme +
  annotate("text", x = min(sensor_bpm) + 2, y = max(watch_bpm) - 2, 
           label = "Línea ideal (y=x)", color = "#06D6A0", size = 3.5, fontface = "italic") +
  coord_equal(ratio = 1) +
  scale_x_continuous(breaks = pretty_breaks(n = 6)) +
  scale_y_continuous(breaks = pretty_breaks(n = 6))

# 2. Series temporales elegante
time_points <- seq(0, (length(sensor_bpm) - 1) * 2, by = 2)

# Crear dataframe para series temporales
time_series_df <- data.frame(
  tiempo = rep(time_points, 2),
  bpm = c(sensor_bpm, watch_bpm),
  dispositivo = factor(rep(c("Sensor PPG", "Samsung Watch 6"), each = length(sensor_bpm)))
)

time_series_plot <- ggplot(time_series_df, aes(x = tiempo, y = bpm, color = dispositivo, shape = dispositivo)) +
  geom_line(size = 1, alpha = 0.8) +
  geom_point(size = 2.5, alpha = 0.9) +
  scale_color_manual(values = c("Sensor PPG" = "#2E86AB", "Samsung Watch 6" = "#E63946")) +
  scale_shape_manual(values = c("Sensor PPG" = 16, "Samsung Watch 6" = 17)) +
  labs(
    title = "Comparación Temporal",
    subtitle = sprintf("RMSE: %.2f BPM", rmse),
    x = "Tiempo (segundos)",
    y = "BPM",
    color = "Dispositivo",
    shape = "Dispositivo"
  ) +
  elegant_theme +
  scale_x_continuous(breaks = pretty_breaks(n = 8)) +
  scale_y_continuous(breaks = pretty_breaks(n = 6)) +
  guides(
    color = guide_legend(override.aes = list(size = 3)),
    shape = guide_legend(override.aes = list(size = 3))
  )

# Combinar ambas gráficas
combined_plot <- grid.arrange(scatter_plot, time_series_plot, ncol = 2)

# === GRÁFICA ADICIONAL: ANÁLISIS BLAND-ALTMAN ===

# Calcular diferencias y promedios para Bland-Altman
differences <- sensor_bpm - watch_bpm
means <- (sensor_bpm + watch_bpm) / 2
mean_diff <- mean(differences)
std_diff <- sd(differences)
limits_of_agreement <- c(mean_diff - 1.96 * std_diff, mean_diff + 1.96 * std_diff)

cat(sprintf("\n=== ANÁLISIS BLAND-ALTMAN ===\n"))
cat(sprintf("Bias (diferencia promedio): %.2f BPM\n", mean_diff))
cat(sprintf("Límites de concordancia (95%%): [%.2f, %.2f] BPM\n", 
            limits_of_agreement[1], limits_of_agreement[2]))
cat(sprintf("Desviación estándar de diferencias: %.2f BPM\n", std_diff))

# Crear dataframe para Bland-Altman
bland_altman_df <- data.frame(
  promedio = means,
  diferencia = differences
)

bland_altman_plot <- ggplot(bland_altman_df, aes(x = promedio, y = diferencia)) +
  geom_point(alpha = 0.7, size = 3, color = "#2E86AB") +
  geom_hline(yintercept = mean_diff, color = "#E63946", size = 1) +
  geom_hline(yintercept = limits_of_agreement[1], color = "#E63946", linetype = "dashed", size = 1) +
  geom_hline(yintercept = limits_of_agreement[2], color = "#E63946", linetype = "dashed", size = 1) +
  geom_hline(yintercept = 0, color = "#06D6A0", linetype = "dotted", size = 1) +
  labs(
    title = "Análisis Bland-Altman",
    subtitle = sprintf("Bias: %.2f BPM, LoA: ±%.2f BPM", mean_diff, 1.96 * std_diff),
    x = "Promedio de ambas mediciones (BPM)",
    y = "Diferencia (Sensor - Watch) (BPM)"
  ) +
  elegant_theme +
  annotate("text", x = max(means) - 2, y = mean_diff + 0.5, 
           label = sprintf("Bias: %.2f", mean_diff), color = "#E63946", size = 3.5) +
  annotate("text", x = max(means) - 2, y = limits_of_agreement[1] - 0.5, 
           label = sprintf("LoA: %.2f", limits_of_agreement[1]), color = "#E63946", size = 3) +
  annotate("text", x = max(means) - 2, y = limits_of_agreement[2] + 0.5, 
           label = sprintf("LoA: %.2f", limits_of_agreement[2]), color = "#E63946", size = 3)

# Mostrar gráfica Bland-Altman
print(bland_altman_plot)

# === RESUMEN ESTADÍSTICO FINAL ===
cat("\n=== RESUMEN ESTADÍSTICO ===\n")
cat(sprintf("Datos analizados: %d pares de mediciones\n", length(sensor_bpm)))
cat(sprintf("Sensor PPG - Media: %.1f BPM, SD: %.1f BPM\n", mean(sensor_bpm), sd(sensor_bpm)))
cat(sprintf("Samsung Watch - Media: %.1f BPM, SD: %.1f BPM\n", mean(watch_bpm), sd(watch_bpm)))