# ZeroMerma - Checklist de alistamiento y runbook para piloto POS

Generado el 2026-04-23.

Objetivo:
- preparar un piloto real de panaderia con el POS de ZeroMerma
- dejar claro que esta soportado hoy y que sigue bloqueado
- evitar prometer capacidades no implementadas

Alcance:
- POS web
- API
- worker
- PostgreSQL
- hardware de caja
- procedimientos operativos de apertura, venta, devolucion, merma, transferencias y cierre

Referencias del repo:
- `scripts/dev/start-local.ps1`
- `scripts/dev/run-operational-regression.ps1`
- `scripts/bootstrap/seed-local-data.py`
- `scripts/bootstrap/seed-training-data.py`
- `docs/implementation/final-pos-consistency-audit.md`
- `docs/implementation/training-mode.md`
- `docs/implementation/customer-communication-readiness.md`
- `docs/implementation/cash-close-contract-map.md`

## 1. Configuracion de ambiente

### Requerido para piloto

- PostgreSQL operativo y monitoreado
- API levantada con variables de entorno explicitas
- worker levantado contra la misma base de datos que la API
- POS web apuntando al `VITE_API_BASE_URL` correcto
- CORS configurado para la URL real del POS
- secretos de autenticacion distintos a desarrollo local

### Variables minimas

Basadas en `.env.example`:

```env
ZEROMERMA_API_ENVIRONMENT=production-or-staging
ZEROMERMA_API_DATABASE_URL=postgresql+psycopg://...
ZEROMERMA_API_AUTH_TOKEN_SECRET=...
ZEROMERMA_API_AUTH_TOKEN_TTL_MINUTES=480

ZEROMERMA_WORKER_ENVIRONMENT=production-or-staging
ZEROMERMA_WORKER_DATABASE_URL=postgresql+psycopg://...
ZEROMERMA_WORKER_POLL_INTERVAL_SECONDS=5
ZEROMERMA_WORKER_BATCH_SIZE=25
```

### Variables operativas sensibles que deben revisarse antes del piloto

```env
ZEROMERMA_API_WASTE_HIGH_IMPACT_QUANTITY_THRESHOLD=10
ZEROMERMA_API_CORRECTION_HIGH_IMPACT_QUANTITY_THRESHOLD=10
ZEROMERMA_API_DISCOUNT_HIGH_VALUE_AMOUNT_THRESHOLD=200
ZEROMERMA_API_RETURN_HIGH_REFUND_AMOUNT_THRESHOLD=200
ZEROMERMA_API_RETURN_OLD_SALE_DAYS_THRESHOLD=7
```

### Dependencias no resueltas para produccion

- no existe configuracion real de proveedor de email/SMS
- no existe exportacion PDF general de documentos operativos
- no existe reporte imprimible/exportable de cierre de caja
- no existe modo offline operativo

## 2. Requisitos de datos semilla

### Desarrollo local

El script `scripts/bootstrap/seed-local-data.py` prepara referencias utiles para pruebas:

- sucursales:
  - `MAIN`
  - `NORTE`
  - `SUR`
- estaciones:
  - `POS-01`
  - `POS-NORTE-01`
  - `POS-SUR-01`
- usuario:
  - `cashier@zeromerma.local`
  - password local conocida por el seed

### Para piloto real

No usar el seed local como configuracion final de produccion. Antes del piloto se requiere:

- catalogo real de productos y clases
- sucursal real del piloto
- al menos una estacion real por caja
- usuario nominal por cajero
- asignacion activa de cada usuario a su sucursal
- motivos operativos revisados:
  - devoluciones
  - mermas
  - ajustes
  - pagos
  - descuentos

### Politica recomendada

- usar datos reales de la sucursal piloto
- no operar el piloto con cuentas compartidas
- mantener un ambiente de entrenamiento separado si se va a capacitar antes del arranque

## 3. Configuracion de sucursal y estacion

Antes del piloto confirmar:

- sucursal con codigo, nombre y timezone correctos
- estacion con codigo fisico visible en caja
- relacion estacion -> sucursal correcta
- branding por sucursal validado si aplica
- reloj del equipo sincronizado

Checklist:

- [ ] codigo de sucursal correcto
- [ ] timezone correcto
- [ ] codigo de estacion correcto
- [ ] nombre visible de la estacion correcto
- [ ] la estacion pertenece a la sucursal correcta
- [ ] la estacion aparece en bootstrap y cash-session-open

## 4. Cuentas de cajero, roles y configuracion de notificaciones a backoffice

### Cuentas de cajero

Estado actual del producto:

- existe autenticacion nominal por usuario
- existe asignacion activa usuario -> sucursal
- no existe un modelo formal de roles/permisos separado
- las operaciones sensibles se controlan por reglas de negocio, auditoria y confirmaciones, no por un gate de rol extra

Recomendacion de piloto:

- una cuenta por cajero
- no usar una sola cuenta para toda la sucursal
- desactivar usuarios que ya no operen

Checklist:

- [ ] cada cajero tiene cuenta propia
- [ ] cada cuenta tiene branch assignment activo
- [ ] no hay cuentas compartidas en piso
- [ ] el password inicial fue rotado

### Roles

Limitacion actual:

- no hay RBAC formal para separar cajero, supervisor y backoffice

Implicacion operativa:

- la aprobacion de operaciones de alto impacto se resuelve hoy con acknowledgement y trazabilidad, no con cambio de rol dentro del sistema

### Notificaciones a backoffice

Estado actual:

- existen eventos/audit trail listos para ciertas operaciones de alto impacto
- no existe entrega real a correo, SMS o bandeja de backoffice
- no existe configuracion de destinatarios finales dentro del producto

Politica para piloto:

- definir destinatarios manuales fuera del sistema
- revisar auditoria y outbox como fuente de seguimiento tecnico
- no anunciar "notificaciones automaticas" como capacidad operativa del piloto

## 5. Checklist de hardware

### Impresora

Estado actual:

- ticket de venta: impresion por navegador disponible
- comprobante de devolucion: impresion por navegador disponible
- documentos operativos en general: impresion aun no implementada
- cierre de caja: reporte imprimible/exportable no implementado

Checklist:

- [ ] navegador permite `window.print` y popup de impresion
- [ ] impresora configurada para ticket de venta
- [ ] impresora validada para comprobante de devolucion
- [ ] politica manual definida para documentos sin impresion soportada

### Cajon de efectivo

Estado actual:

- hay operaciones que afectan caja
- no hay integracion automatica con apertura fisica del cajon

Checklist:

- [ ] procedimiento manual de apertura/cierre del cajon definido
- [ ] responsable de resguardo de efectivo definido

### Scanner

Estado actual:

- soporte para scanner tipo keyboard-wedge
- no hay soporte para camara, HID avanzado o serial

Checklist:

- [ ] scanner probado como entrada de teclado
- [ ] lectura de codigo de producto validada
- [ ] lectura de folio de ticket validada
- [ ] lectura de folio de envio validada

### Terminal bancaria

Estado actual:

- ventas y pagos contemplan tarjeta como metodo
- reverso de tarjeta en devoluciones sigue pendiente de integracion
- no hay integracion directa con terminal de pago externa

Checklist:

- [ ] conciliacion manual con terminal definida
- [ ] flujo manual para devoluciones a tarjeta documentado

## 6. SOP de apertura de caja

1. Iniciar sesion con cuenta nominal.
2. Confirmar sucursal y estacion.
3. Capturar efectivo contado inicial.
4. Verificar que la caja quede en estado abierta.
5. Entrar al POS.

Controles:

- apertura de caja es obligatoria antes de operar
- no abrir segunda caja para el mismo usuario o la misma estacion
- si la caja ya esta abierta, usar `Ir al POS`

Checklist:

- [ ] correo y password correctos
- [ ] sucursal/estacion correctas
- [ ] monto inicial capturado
- [ ] caja abierta visible en pantalla

## 7. SOP de venta

1. Confirmar que la caja este abierta.
2. Capturar venta por:
   - `PRODUCT_DIRECT`, o
   - `CLASS_CAPTURE`
3. Agregar lineas con teclado o mouse.
4. Cobrar.
5. Confirmar venta.
6. Imprimir ticket si el cliente lo requiere.

Controles:

- no alterar la semantica de `PRODUCT_DIRECT` y `CLASS_CAPTURE`
- monto insuficiente debe bloquear confirmacion
- la venta confirmada debe dejar folio y ticket consultable

Checklist:

- [ ] venta registrada con folio
- [ ] ticket visible en modulo Tickets
- [ ] impresion de ticket validada

## 8. SOP de devolucion

1. Buscar la venta por folio o desde Tickets.
2. Seleccionar lineas devolvibles.
3. Capturar cantidad.
4. Capturar motivo obligatorio.
5. Elegir metodo de reembolso.
6. Confirmar devolucion.
7. Imprimir comprobante si aplica.

Controles:

- motivo obligatorio
- metodo de reembolso obligatorio
- tarjetas y mixto no deben anunciarse como integrados si siguen pendientes
- ventas viejas o montos altos requieren acknowledgement, no bloqueo por rol

Checklist:

- [ ] venta origen localizada
- [ ] lineas correctas seleccionadas
- [ ] motivo capturado
- [ ] metodo de reembolso correcto
- [ ] comprobante generado o politica manual definida

## 9. SOP de merma

1. Seleccionar origen.
2. Seleccionar motivo.
3. Capturar lineas y cantidades.
4. Agregar notas si el motivo lo requiere o si es alto impacto.
5. Revisar bloqueos y resumen.
6. Confirmar merma.

Controles:

- sin origen, motivo o lineas no se registra
- para ciertos motivos y alto impacto se requieren notas
- no existen adjuntos reales; la evidencia hoy es nota operativa
- validacion de stock solo aplica donde el contrato backend existe

Checklist:

- [ ] origen capturado
- [ ] motivo capturado
- [ ] lineas capturadas
- [ ] notas agregadas cuando corresponda
- [ ] folio de merma visible

## 10. SOP de traspaso, envio y recepcion

### Pasar a mostrador

1. Seleccionar productos.
2. Capturar cantidades.
3. Revisar resumen.
4. Confirmar traspaso.

### Enviar a sucursal

1. Seleccionar sucursal destino.
2. Revisar ruta sugerida.
3. Capturar productos y cantidades.
4. Confirmar envio.

### Recibir envio

1. Seleccionar envio pendiente.
2. Capturar cantidades recibidas.
3. Si hay diferencias, capturar motivo por linea.
4. Confirmar recepcion.

Controles:

- envio requiere destino y lineas
- recepcion parcial o con diferencia requiere motivo
- historial y detalle deben quedar consultables
- impresion de estos documentos aun no esta implementada

Checklist:

- [ ] traspaso registrado con folio
- [ ] envio registrado con folio
- [ ] recepcion exacta validada
- [ ] recepcion con diferencia validada
- [ ] politica manual para comprobante impreso definida

## 11. SOP de cierre de caja

1. Confirmar que existe caja abierta.
2. Revisar resumen del turno.
3. Capturar conteo de efectivo total.
4. Revisar conciliacion por metodo de pago.
5. Revisar conciliacion de class capture si aplica.
6. Revisar diferencias.
7. Acknowledgement del cajero si hay diferencia relevante.
8. Confirmar cierre.

Controles:

- el cierre es obligatorio
- el backend decide preview y commit final
- no hay conteo por denominacion de billete/moneda
- no hay reporte imprimible/exportable final

Checklist:

- [ ] preview ejecutado sin bloqueos
- [ ] diferencias revisadas
- [ ] acknowledgement aplicado cuando corresponda
- [ ] cierre confirmado
- [ ] detalle de cierre consultable

## 12. Manejo de incidentes

### Incidente: API no responde

Politica:

- detener nuevas operaciones irreversibles
- no seguir vendiendo "para capturar despues" dentro del sistema
- escalar a soporte tecnico

### Incidente: base de datos degradada o sin respuesta

Politica:

- detener piloto
- revisar salud de PostgreSQL
- no reiniciar operacion sin validar integridad

### Incidente: worker caido

Impacto:

- operaciones principales pueden persistir
- procesamiento de outbox queda rezagado

Accion:

- levantar worker
- revisar backlog de `outbox_events`

### Incidente: impresora falla

Politica:

- continuar solo si la sucursal acepta operacion con politica manual de comprobantes
- documentar el incidente y reimprimir cuando el hardware regrese

### Incidente: diferencia de caja alta

Politica:

- no borrar ni corregir fuera del flujo auditado
- registrar cierre con razones y acknowledgement donde aplique
- revisar auditoria y documentos generados

## 13. Politica de modo offline o degradado

Estado actual:

- no existe modo offline operativo
- no existe cola local para capturar ventas fuera de linea
- el backend sigue siendo la unica fuente de verdad

Politica de piloto:

- si API o base de datos no estan disponibles, detener captura nueva
- si la sucursal necesita continuidad manual, usar procedimiento externo temporal y recaptura supervisada fuera del flujo normal
- no mezclar recaptura manual con operacion en vivo sin conciliacion posterior

## 14. Politica de respaldo y auditoria

### Respaldo

Requerido para piloto:

- backup diario de PostgreSQL
- politica de restauracion probada
- retencion definida
- idealmente PITR si el piloto es operativo real

### Auditoria

El sistema ya deja trazas utiles para operaciones sensibles:

- audit trail
- transactional outbox
- historiales por modulo sensible

Politica:

- no purgar auditoria durante el piloto
- revisar operaciones de alto impacto diariamente
- usar el endpoint dev audit solo para entorno local controlado, no como practica de produccion

## 15. Checklist de capacitacion

### Operacion

- [ ] apertura de caja
- [ ] venta por `PRODUCT_DIRECT`
- [ ] venta por `CLASS_CAPTURE`
- [ ] cobro exacto y con cambio
- [ ] consulta de Tickets
- [ ] devolucion con motivo y metodo
- [ ] merma con origen y motivo
- [ ] envio y recepcion entre sucursales
- [ ] ajuste auditado
- [ ] cierre de caja

### Herramientas

- [ ] uso de teclado y shortcuts
- [ ] uso de scanner tipo teclado
- [ ] impresion de ticket y devolucion
- [ ] lectura de bloqueos y mensajes operativos

### Entrenamiento seguro

- [ ] usar modo entrenamiento con base de datos separada para practicas
- [ ] no usar produccion para entrenamiento

## 16. Criterios Go / No-Go

### Go

Se puede arrancar piloto si:

- [ ] API, worker y PostgreSQL estan estables
- [ ] migraciones aplicadas
- [ ] sucursal y estacion reales configuradas
- [ ] cuentas nominales creadas y probadas
- [ ] flujo de apertura, venta, devolucion, merma, envio/recepcion y cierre probado en la sucursal piloto
- [ ] impresion de ticket y devolucion validada
- [ ] respaldo y monitoreo definidos
- [ ] procedimiento de incidentes comunicado al equipo
- [ ] suite frontend y e2e relevante en verde
- [ ] suite backend DB-backed rerun en un entorno con PostgreSQL responsivo

### No-Go

No salir a piloto si ocurre cualquiera de estos puntos:

- [ ] la base de datos o el worker no estan estables
- [ ] no existen cuentas nominales por cajero
- [ ] la sucursal o la estacion estan mal configuradas
- [ ] no se validaron apertura y cierre de caja
- [ ] no se valido la impresion de ticket
- [ ] no existe politica operativa para devoluciones a tarjeta pendientes
- [ ] no existe politica operativa para documentos sin impresion soportada
- [ ] no se rerun la suite backend DB-backed

## Brechas que hoy bloquean un piloto mas completo

Estas no bloquean necesariamente un piloto controlado, pero si limitan el alcance real:

- no hay notificaciones reales a clientes ni a backoffice
- no hay offline mode
- no hay impresion/exportacion general de documentos operativos
- no hay reporte imprimible/exportable de cierre de caja
- no hay RBAC formal
- no hay integracion directa con cajon de efectivo
- no hay integracion directa con terminal bancaria
- reverso de tarjeta en devoluciones sigue pendiente

## Recomendacion operativa final

Para un piloto real, ZeroMerma esta mas cerca de un piloto controlado de sucursal unica o de pocas cajas, con personal entrenado y soporte tecnico cercano, que de un despliegue autonomo sin acompanamiento.

La salida recomendada es:

1. ambiente productivo o staging muy cercano a produccion
2. una sucursal piloto
3. una o dos cajas maximo al inicio
4. entrenamiento previo en base separada
5. acompanamiento de soporte durante apertura, hora pico y cierre de los primeros dias
