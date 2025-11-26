/**
 * Service Worker en Segundo Plano de la Extensión Chrome Cheapy
 *
 * Punto de entrada principal para scripts en segundo plano. Este service worker se ejecuta
 * persistentemente en segundo plano y coordina varias funcionalidades de la extensión
 * incluyendo detección de búsquedas y comunicación con API.
 */

import { initializeDetectarBusqueda } from './background/detectar_busqueda.js';

/**
 * Inicializa todos los servicios en segundo plano cuando la extensión se inicia.
 * Esto incluye configurar mecanismos de detección de búsquedas que monitorean
 * el comportamiento de navegación del usuario para activar búsquedas de comparación de precios.
 */
initializeDetectarBusqueda();