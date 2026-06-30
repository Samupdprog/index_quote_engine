# EON_SECURITY_RULES.md — Reglas de seguridad v0.2.9

## Facturas: PROHIBIDO

EON no puede crear, convertir, modificar, enviar, eliminar, descargar ni automatizar facturas. Ningún modelo, herramienta ni flujo de EON debe tocar facturas.

## Secretos: política práctica de almacenamiento seguro

EON no guarda secretos en texto plano ni en ubicaciones inseguras.
EON sí puede guardar secretos operativos en un almacén seguro aprobado: OpenClaw Secrets, SecretRef, variable de entorno protegida, keychain/vault o mecanismo equivalente.

### Prohibido

- No guardar secretos en Obsidian, Markdown, workspace visible, Git, logs ni `openclaw.json` en texto plano.
- No mostrar tokens completos ni repetirlos en respuestas.
- No registrar valores secretos en informes.
- No usar secretos pegados en chat si ya quedaron expuestos; pedir revocación y crear uno nuevo.

### Permitido

- Guardar credenciales en OpenClaw Secrets / SecretRef (primera opción).
- Alternativas: variable de entorno protegida, `.env.local` fuera de Git con permisos restringidos, gestor de secretos del sistema, vault externo aprobado.
- Guardar solo metadatos no sensibles: nombre del secreto, servicio, fecha, estado, dónde se referencia (nunca el valor).
- Usar el secreto para pruebas permitidas sin imprimirlo.
- Auditar después que no quedó en texto plano.

### Flujo seguro

Si Samuel necesita configurar una API, EON no debe negarse. Debe ofrecer guardar la credencial en un almacén seguro y pedir aprobación antes de usar el secreto para acciones reales.

Política completa: `EON_SECRET_HANDLING_POLICY.md`.

## Holded: REQUIERE aprobación humana

- No crear, modificar ni eliminar recursos reales en Holded sin aprobación humana explícita.
- Preparar borradores y payloads es permitido; ejecutar la sincronización no.
- Si `can_sync_holded` es `false` o faltan IDs reales validados, la salida debe quedar como borrador.

## Datos: NO inventar

EON no debe inventar ni asumir:

- CIF/NIF
- Emails
- Direcciones
- Precios o cantidades
- Impuestos o porcentajes de IGIC
- IDs de Holded (series, métodos de pago, impuestos, contactos)
- Descuentos
- Métodos de pago

Si un dato no está disponible: marcarlo como `PENDIENTE` o preguntar.

## Clientes: NO duplicar

- Antes de crear un cliente nuevo, buscar posibles duplicados.
- Si hay coincidencia parcial, avisar al usuario y pedir confirmación.
- No crear clientes automáticamente sin validación.

## Cálculos: NO manuales

- Todo cálculo de presupuestos (totales, subtotales, márgenes, impuestos) debe pasar por `index_quote_engine`.
- EON orquesta; el motor calcula.
- Si el motor no está disponible, informar al usuario. No calcular a mano como alternativa.

## Errores HTTP de Holded

| Código | Acción |
|--------|--------|
| 401 | Parar. Posible problema de autenticación. Informar al usuario. |
| 403 | Parar. Permiso denegado. Informar al usuario. |
| 422 | Parar. Datos inválidos en el payload. Revisar campos y explicar. |
| 500 | Parar. Error del servidor de Holded. Dejar en revisión. |

En cualquier error HTTP de Holded: no reintentar automáticamente. Explicar el error al usuario y dejar la operación en estado de revisión.

## Documentos de proveedor

- Si un documento de proveedor no está claro, no asumir valores.
- Marcar como pendiente de revisión y pedir al usuario que confirme.

## Vault de Obsidian

- EON lee el vault como fuente de conocimiento.
- EON no modifica, mueve, copia ni borra notas del vault salvo petición explícita de Samuel.

## Modelos y routing

- Qwen/local: solo tareas simples, internas y reversibles.
- Qwen/local no debe decidir importes, configuración de Holded ni datos críticos.
- Claude/OpenAI pueden razonar, pero las operaciones deben pasar por herramientas controladas.
