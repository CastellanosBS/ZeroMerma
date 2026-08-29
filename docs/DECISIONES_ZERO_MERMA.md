# Decisiones canónicas de ZeroMerma

**Condición:** única fuente versionada para registrar `DEC-01`–`DEC-20` y sus futuras revisiones.
**Propietario de las decisiones:** propietario de ZeroMerma.
**Última actualización:** 2026-08-27.
**Fuente normativa:** `PLAN_MAESTRO_FINALIZACION_ZERO_MERMA.md`, fecha de consolidación 2026-08-25, sección “Decisiones pendientes del propietario”, con contenido normativo suministrado por el propietario durante `ZM-FIN-002`.

## Reglas de gobierno

1. Este archivo es el único registro canónico versionado de decisiones de ZeroMerma. Los documentos técnicos pueden desarrollar una decisión, pero deben referenciar este registro y no sustituirlo.
2. Los estados permitidos son `PENDIENTE`, `APROBADA` y `SUSTITUIDA`.
3. Sólo el propietario de ZeroMerma puede aprobar una decisión o cambiar su estado a `APROBADA`. Codex puede inspeccionar, preparar alternativas y registrar una aprobación expresa, pero no decidir por el propietario.
4. Una propuesta, inferencia técnica, recomendación o implementación no constituye por sí misma una decisión aprobada.
5. Toda revisión debe conservar estado, fecha, propietario, evidencia, tareas afectadas, consecuencias y el historial de la decisión sustituida o modificada.
6. Una decisión `SUSTITUIDA` debe conservar su contenido histórico y enlazar la decisión o revisión que la sustituye.
7. No se crearán decision logs, índices DEC, roadmaps, planes maestros ni matrices de alcance paralelos.
8. El estado de una decisión no certifica por sí solo código, funcionalidad, seguridad, migraciones, datos, pruebas ni preparación para producción.

### Nota de procedencia documental

Durante `ZM-FIN-002` se observaron tres huellas integrales diferentes atribuidas a copias o transportes del Plan Maestro. No existe evidencia suficiente para explicar la diferencia ni seleccionar una de ellas. En consecuencia, este registro no declara ninguna huella integral del Plan Maestro como canónica. La fuente normativa de esta versión es la sección DEC-01–DEC-20 reproducida literalmente por el propietario durante `ZM-FIN-002`; la discrepancia documental no modifica ninguna decisión.

## DEC-01 — Línea base canónica

- **Estado:** `APROBADA`
- **Fecha:** 2026-08-26
- **Propietario:** propietario de ZeroMerma
- **Qué decide:** qué cambios locales o no rastreados forman parte del snapshot preservado y qué commit constituye la fuente técnica de verdad.

### Resolución aprobada

- Commit canónico: `8e598c26c14edd76e5400ec9a040b21f91a7dd7c`.
- Tree: `5760a3b4fb1eb9bd28235808c98c7329ab617569`.
- Padre: `c058eba850d1f6f504bf3dbe19f23fe620fb2f16`.
- Rama: `baseline/zeromerma-finalizacion-2026-08-26`.
- Tag: `zeromerma-baseline-2026-08-26`.
- Fingerprint Git del snapshot original: `484d5950b3e822e45f098169aa3ae20488defc13e33208e16cad8e8b9ae7a92a`.
- Fingerprint del contenido no ignorado: `9acf6284c7c2ce8b2bdddfc3933c5debe8c5a4d172040468a6a633ae0e9ea98f`.

El commit constituye una línea base de preservación: fija de forma inmutable el contenido no ignorado aprobado por el propietario para continuar el Plan Maestro. No reconstruye ni aprueba la historia funcional de sus cambios.

### Límites de la aprobación

DEC-01 no constituye aprobación funcional, de pruebas, migraciones, contratos OpenAPI, cliente generado, seguridad, integridad de datos ni preparación para producción. Tampoco valida individualmente la eliminación histórica de `apps/pos-web/src/features/cash-close/ui.tsx`.

### Evidencia, tareas y consecuencias

- **Evidencia principal:** cierre de `ZM-FIN-001`, commit, tree, rama y tag anteriores; estado Git limpio posterior; manifiesto y fingerprints del snapshot preservado.
- **Tareas afectadas:** `ZM-FIN-001` y todas las tareas posteriores que deben partir de esta revisión.
- **Gate afectado:** Baseline Ready.
- **Consecuencia:** toda inspección, cambio, validación o evidencia posterior debe identificar esta línea base o un descendiente atribuible.
- **Historial:** aprobación inicial; no sustituye una decisión canónica anterior.

## DEC-02 — Alcance y visibilidad

- **Estado:** `APROBADA`
- **Fecha:** 2026-08-26
- **Propietario:** propietario de ZeroMerma
- **Qué decide:** qué capacidades pertenecen al producto final y qué política de visibilidad deben tener mientras se completan y validan.

### Directrices aprobadas

1. ZeroMerma se finalizará como sistema integral, no como reducción silenciosa a un MVP.
2. Ninguna capacidad productiva se excluye únicamente por estar incompleta.
3. Una capacidad incompleta debe ocultarse o mostrarse inequívocamente como no disponible hasta completar y validar su vertical.
4. Ninguna superficie simulada, placeholder, desconectada o sin efecto real puede aparentar operación productiva.
5. Una capacidad visible pendiente de validación no se considera funcionalmente aprobada ni autorizada para producción.
6. Training queda fuera del entorno productivo, pero puede conservarse para un entorno y una base de datos separados.
7. Health y los controles operativos se conservan técnicamente, pero no forman parte del catálogo funcional de usuario.
8. Los aliases administrativos no son rutas canónicas; sólo pueden conservarse durante una transición controlada.
9. Ninguna disposición de DEC-02 sustituye las decisiones técnicas o de negocio posteriores DEC-03–DEC-20.

### Distribución canónica

| Disposición | Cantidad |
|---|---:|
| `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | 38 |
| `INCLUIDA_OCULTA_HASTA_COMPLETARSE` | 24 |
| `INCLUIDA_BLOQUEADA_POR_DECISION` | 11 |
| `EXCLUIDA_OBSOLETA_DUPLICADA_O_INTERNA` | 6 |
| `REQUIERE_DECISION_DEL_PROPIETARIO` | 0 |
| **Total** | **79** |

### Correcciones canónicas sobre la matriz original

- `POS-BO-01`: `REQUIERE_DECISION_DEL_PROPIETARIO` → `INCLUIDA_BLOQUEADA_POR_DECISION`; vinculada a DEC-05. El traspaso actual de bearer mediante URL no está autorizado para producción.
- `POS-OPDISC-01`: `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` → `INCLUIDA_OCULTA_HASTA_COMPLETARSE`; vinculada a DEC-13 hasta diferenciar inequívocamente su nombre y semántica de los descuentos comerciales.

### Vinculaciones normativas

- RBAC → DEC-03.
- Scopes → DEC-04.
- Sesión y traspaso POS–Backoffice → DEC-05.
- Pagos externos → DEC-14.
- Hardware y offline → DEC-15.
- Fiscalidad, tickets, privacidad, retención, exportación, comunicaciones y consentimiento → DEC-16.
- Plataforma y continuidad → DEC-17.
- Métricas y alertas → DEC-18.
- Datos existentes → DEC-19 cuando corresponda.
- Piloto y rollout → DEC-20 cuando corresponda.

### Responsabilidades de tareas

- `ZM-FIN-008` construye la matriz funcional detallada ruta–caso de uso–persistencia–estado real.
- `ZM-FIN-015`–`ZM-FIN-022` implementan RBAC y scopes.
- `ZM-FIN-004`–`ZM-FIN-006` establecen toolchain, base segura y migraciones como precondiciones de validación; no sustituyen pruebas funcionales.
- Las tareas funcionales posteriores completan las verticales ocultas o bloqueadas en el orden del Plan Maestro.

### Evidencia, consecuencias e historial

- **Evidencia principal:** inspección estática de `ZM-FIN-002`; 16 rutas POS, 12 entradas POS, 40 rutas hoja Backoffice, 32 módulos Backoffice, 46 registros de routers API, 45 familias API, 224 operaciones decoradas y un worker sin handlers efectivos.
- **Consecuencias:** las políticas de navegación, acceso directo, flags y acciones deben implementarse y probarse antes de cerrar `ZM-FIN-002`; esta aprobación no valida ninguna de las 79 capacidades.
- **Tareas afectadas:** `ZM-FIN-002`, `ZM-FIN-004`–`ZM-FIN-006`, `ZM-FIN-008`, `ZM-FIN-015`–`ZM-FIN-022` y las tareas funcionales vinculadas por la matriz.
- **Historial:** aprobación inicial con dos reclasificaciones expresas; no sustituye una DEC-02 canónica anterior.

### Anexo DEC-02 — Matriz canónica de 79 capacidades

#### Naturaleza del anexo

Este anexo es la matriz canónica de alcance y visibilidad aprobada por DEC-02. Su propósito es registrar la identidad de cada capacidad, su estado real observado estáticamente, su disposición de alcance, la política de visibilidad aplicable, las decisiones pendientes relacionadas, las tareas del Plan Maestro y la evidencia principal.

El anexo es deliberadamente compacto y no pretende reproducir campo por campo la matriz técnica de inspección utilizada para preparar DEC-02.

La matriz exhaustiva de rutas y operaciones, incluyendo autenticación, permisos, scopes, endpoints, servicios, transacciones, entidades, persistencia, auditoría, outbox, consumidores UI y pruebas, será construida, validada y versionada en `ZM-FIN-008`.

La clasificación `REAL_INTEGRADA` y la disposición `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` no constituyen validación funcional ni autorización para producción.

Las tareas `ZM-FIN-004`–`ZM-FIN-006` son precondiciones, no sustitutos de la validación funcional posterior.

| surface_id | Aplicación/subsistema | Módulo | Ruta o acceso | Capacidad | Estado real | Disposición canónica | Política de visibilidad | Decisión vinculada | Tareas relacionadas | Evidencia principal | Archivos/rutas a modificar posteriormente | Contradicción o evidencia pendiente |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| POS-AUTH-01 | POS | Acceso | `/login` | Autenticar usuario | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Mostrar login hasta autenticar; no implica sesión productiva validada | DEC-05 | `ZM-FIN-002`; `ZM-FIN-004`–`006`; validación funcional posterior | `apps/pos-web/src/router.tsx`; `apps/pos-web/src/features/auth/login-page.tsx`; `auth-api.ts`; API identity | Router y feature auth | Seguridad dinámica de sesión pendiente |
| POS-BOOT-01 | POS | Bootstrap | Rutas protegidas | Resolver usuario, sucursal, estación, caja y training | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Gate obligatorio antes de operar | DEC-04, DEC-05 | `ZM-FIN-002`; `ZM-FIN-004`–`006`; `ZM-FIN-015`–`022` | `apps/pos-web/src/features/pos-bootstrap/pos-bootstrap-api.ts`; `PosProtectedLayout`; `/v1/pos/bootstrap` | Layout y router POS | Las rutas profundas no comparten una única redirección por caja |
| POS-CASH-01 | POS | Caja | `/cash-session/open` | Consultar y abrir turno | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Visible sin turno; apertura obligatoria | DEC-02 | `ZM-FIN-002`; precondiciones `ZM-FIN-004`–`006`; validación funcional posterior | `cash-session-open-screen.tsx`; `cash-session-api.ts`; módulo API cash | Pantalla, layout y router | Atomicidad y ciclo completo no ejecutados |
| POS-SALE-01 | POS | Venta | `/pos` | Catálogo, clases, scanner y carrito | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Visible con turno y permisos efectivos | DEC-02 | `ZM-FIN-002`; `ZM-FIN-008`; `ZM-FIN-015`–`022`; validación posterior | `pos-terminal-api.ts`; `pos-scanner-input.tsx`; `scanner.ts`; `/v1/pos/catalog` | POS terminal, módulos y gates | Scanner sólo keyboard wedge; hardware adicional pendiente |
| POS-SALE-02 | POS | Venta | `/pos` | Confirmar PRODUCT_DIRECT/CLASS_CAPTURE y registrar efectivo, tarjeta o mixto | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Candidata visible; no operativa hasta validar ledgers, permisos e idempotencia | DEC-02 | `ZM-FIN-008`; tareas funcionales y de seguridad posteriores | `pos-terminal-api.ts`; `/v1/sales/confirm`; módulos sales/payments/outbox/audit | Venta POS, servicio sales y gates | Tarjeta registra medio contable, no autorización externa |
| POS-PAYEXT-01 | POS | Pago externo | Acción tarjeta | Autorizar y capturar con terminal/proveedor | `DESCONECTADA` | `INCLUIDA_BLOQUEADA_POR_DECISION` | Deshabilitar cualquier apariencia de cobro externo | DEC-14 | `ZM-FIN-002`; tarea posterior de pagos externos | Config `integrations.payment_terminal_status`; ausencia de adapter/provider | UI de pago, adapter, configuración y servicio | Proveedor, hardware, reversas y estados no definidos |
| POS-IDEM-01 | POS | Venta | Confirmación | Prevenir doble envío y replay | `PARCIAL` | `INCLUIDA_OCULTA_HASTA_COMPLETARSE` | No habilitar operación productiva hasta idempotencia backend | DEC-02 | Tarea posterior de idempotencia; validación funcional | Estado de submit y pruebas UI; ausencia de idempotency key persistente | Cliente, router y servicio de venta | El bloqueo de doble clic no cubre reintentos de red |
| POS-COUNTER-01 | POS | Mostrador | `/pasar-a-mostrador` | Registrar pase físico | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Candidata visible con turno; pendiente de ledger y pruebas | DEC-02 | `ZM-FIN-008`; tareas funcionales posteriores | `counter-transfer-screen.tsx`; `operations-api.ts`; módulo operations | Feature operations y gates | Concurrencia e inventario canónico no validados |
| POS-TRF-01 | POS | Envíos | `/enviar-a-sucursal` | Preparar y despachar transferencia | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Visible sólo con contexto, scope e integridad validados | DEC-02 | `ZM-FIN-015`–`022`; tareas logísticas posteriores | `dispatch-screen.tsx`; `transfers-api.ts`; módulo transfers | Transfers POS/API y navegación | Recepción concurrente e impresión pendientes |
| POS-TRF-02 | POS | Recepciones | `/recibir-envio` | Recibir envío y registrar diferencias | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Visible sólo con scope y ledger validados | DEC-02 | `ZM-FIN-015`–`022`; tareas logísticas posteriores | `receipt-screen.tsx`; `transfers-api.ts`; módulo transfers | Transfers POS/API y navegación | Hardware/red e inventario canónico no validados |
| POS-ORD-01 | POS | Pedidos | `/pedidos` | Crear pedido y anticipo | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Visible tras validar reconocimiento financiero y físico | DEC-02 | `ZM-FIN-008`; tareas de pedidos posteriores | `orders-screen.tsx`; `orders-api.ts`; módulo orders | Orders POS/API | Conciliación externa y reglas de reserva pendientes |
| POS-ORD-02 | POS | Pedidos | Detalle | Listar, preparar, entregar, cancelar y liquidar | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Visible tras validar estados, caja, inventario y permisos | DEC-02 | Tareas funcionales posteriores; `ZM-FIN-015`–`022` | `orders-api.ts`; endpoints mark-ready/deliver/cancel | Orders UI/API | Falta validación E2E exhaustiva |
| POS-ORD-03 | POS | Pedidos | Acción “pedido listo” | Notificar al cliente | `PLACEHOLDER` | `INCLUIDA_BLOQUEADA_POR_DECISION` | Mantener inequívocamente deshabilitada | DEC-16 | `ZM-FIN-002`; tarea posterior de comunicaciones | `customer-communication.ts`; readiness doc; ausencia de provider/handler | Comunicación, worker y UI | Canal, consentimiento y proveedor no aprobados |
| POS-TKT-01 | POS | Tickets | `/tickets` | Buscar, consultar, reimprimir y abrir impresión del navegador | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Visible tras prueba en hardware certificado | DEC-15, DEC-16 | Tarea funcional/hardware posterior | `tickets-screen.tsx`; `tickets-api.ts`; `features/tickets/print.ts`; `browser-print.ts` | Impresión y pantalla tickets | Compatibilidad real de impresora no verificable estáticamente |
| POS-TKT-02 | POS | Tickets | Detalle | Enviar ticket por correo o SMS | `PLACEHOLDER` | `INCLUIDA_BLOQUEADA_POR_DECISION` | Mantener deshabilitada | DEC-16 | `ZM-FIN-002`; tarea posterior de comunicaciones | `customer-communication.ts`; `document-actions.ts`; ausencia de provider | Comunicación, worker y detalle ticket | Contacto, consentimiento y estados de entrega ausentes |
| POS-RET-01 | POS | Devoluciones | `/devoluciones` | Buscar venta, devolver efectivo e imprimir recibo | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Visible tras validar reversas, caja, inventario y permisos | DEC-02 | `ZM-FIN-008`; tareas funcionales posteriores | `returns-screen.tsx`; `returns-api.ts`; `returns/print.ts`; módulo returns | Returns UI/API | Operación completa no ejecutada en esta tarea |
| POS-RET-02 | POS | Devoluciones | Forma de devolución | Reembolsar tarjeta o mixto | `PLACEHOLDER` | `INCLUIDA_BLOQUEADA_POR_DECISION` | Mantener deshabilitada | DEC-14 | Tarea posterior de pagos externos | Bootstrap deshabilita CARD/MIXED; backend restringe a CASH | Returns y adapter de pagos | Provider, conciliación y reversa no definidos |
| POS-RET-03 | POS | Devoluciones | Detalle | Entregar recibo digital | `PLACEHOLDER` | `INCLUIDA_BLOQUEADA_POR_DECISION` | Mantener deshabilitada | DEC-16 | Tarea posterior de comunicaciones | `customer-communication.ts`; `document-actions.ts` | Comunicación y detalle devolución | Sin proveedor ni consentimiento |
| POS-COR-01 | POS | Correcciones | `/correcciones` | Buscar, consultar y corregir documentos | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Visible con permisos, scope, idempotencia e integridad validados | DEC-02 | `ZM-FIN-015`–`022`; tareas funcionales posteriores | `corrections-screen.tsx`; `corrections-api.ts`; módulo corrections | Corrections UI/API | Concurrencia e impresión pendientes |
| POS-WST-01 | POS | Merma | `/registrar-merma` | Registrar merma y alto impacto | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Visible tras reglas de inventario, merma y autorización | DEC-02 | `ZM-FIN-015`–`022`; tareas funcionales posteriores | `operation-module-screen.tsx`; `operations-api.ts`; módulo waste/operations | Waste UI/API | Política aprobatoria e inventario canónico pendientes |
| POS-OPPAY-01 | POS | Pagos operativos | `/pagos` | Listar, detallar y registrar egreso | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Visible sólo con permisos, caja y conciliación validados | DEC-02 | `ZM-FIN-015`–`022`; tareas financieras posteriores | `payments-screen.tsx`; `payments-api.ts`; módulo payments | Payments UI/API | Tarjeta es registro; mixto no soportado |
| POS-OPDISC-01 | POS | Descuentos operativos | `/descuentos` | Registrar cargo o descuento operativo | `REAL_INTEGRADA` | `INCLUIDA_OCULTA_HASTA_COMPLETARSE` | Ocultar hasta diferenciar nombre y semántica de descuentos comerciales | DEC-13 | `ZM-FIN-002`; tarea funcional de pricing/descuentos | `discounts-screen.tsx`; `discounts-api.ts`; operational discounts/categories | Navegación, etiquetas, contratos y documentación | Concepto distinto de promoción comercial, pero nombre ambiguo |
| POS-CLOSE-01 | POS | Cierre | `/cerrar-turno` | Conteo, conciliación, preview, commit y detalle | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Obligatoria pero no productiva hasta validar concurrencia y reconciliación | DEC-02 | Tareas de cierre e integridad posteriores | `cash-close-screen.tsx`; `cash-close-api.ts`; módulo cash_close | Cash-close UI/API y gates | `ui.tsx` eliminado no era la ruta vigente; pruebas no ejecutadas |
| POS-DOC-01 | POS | Documentos | Detalles operativos | Imprimir o descargar envío, recepción, merma, corrección y cierre | `PLACEHOLDER` | `INCLUIDA_OCULTA_HASTA_COMPLETARSE` | Ocultar o mostrar inequívocamente no disponible | DEC-15, DEC-16 | `ZM-FIN-002`; tarea posterior de documentos/hardware | `document-actions.ts`; `components/document-actions.tsx` | Acciones y pantallas operativas | Sólo copiar folio; impresión/PDF deshabilitados |
| POS-OFF-01 | POS | Offline | Toda operación | Operar sin conexión y sincronizar | `PLACEHOLDER` | `INCLUIDA_BLOQUEADA_POR_DECISION` | No mostrar ni prometer soporte | DEC-15 | Tarea posterior de hardware/offline | Ausencia de service worker, IndexedDB y queue; documentación de contingencia | Bootstrap, almacenamiento y API | Conflictos e idempotencia sin diseño |
| POS-DRAWER-01 | POS | Caja/hardware | Cobro, apertura y cierre | Abrir cajón | `DESCONECTADA` | `INCLUIDA_BLOQUEADA_POR_DECISION` | No mostrar soporte hasta definir dispositivo | DEC-15 | Tarea posterior de hardware | Ausencia de adapter HID/serial/vendor | Adapter de hardware y flujos de caja | Dispositivo no definido |
| POS-BO-01 | POS/Backoffice | Cambio de superficie | Tras login | Acceder de POS a Backoffice | `REAL_INTEGRADA` | `INCLUIDA_BLOQUEADA_POR_DECISION` | No autorizar el bearer por URL; ocultar/bloquear hasta mecanismo aprobado | DEC-05 | `ZM-FIN-002`; tarea de sesión; `ZM-FIN-015`–`022` | `login-form.tsx`; `auth-surfaces.ts`; redirección por fragmento URL | Auth surfaces, login y sesión | Requiere reautenticación o intercambio seguro de un solo uso |
| BO-AUTH-01 | Backoffice | Acceso | `/login` | Autenticar en Backoffice | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Visible; operación posterior sujeta a sesión, RBAC y scopes | DEC-03, DEC-04, DEC-05 | `ZM-FIN-015`–`022`; validación funcional posterior | `apps/backoffice-web/src/router.tsx`; auth client; `/v1/auth/login` | Router y auth Backoffice | Permiso granular separado |
| BO-DASH-01 | Backoffice | Dashboard | `/admin/dashboard`, `/admin` | Mostrar métricas ejecutivas | `SIMULADA` | `INCLUIDA_OCULTA_HASTA_COMPLETARSE` | Ocultar hasta datos reales y KPI aprobados | DEC-18 | `ZM-FIN-002`; tarea posterior de métricas | `adminModules.ts`; `adminData.ts`; `AdminDashboardPage`; `AdminPageShell` | Navegación, dashboard y fuente de datos | `records: []` e `isBackendConnected: false` |
| BO-ALERT-01 | Backoffice | Alertas | `/admin/alertas` | Mostrar alertas y tareas | `SIMULADA` | `INCLUIDA_OCULTA_HASTA_COMPLETARSE` | Ocultar hasta motor, handlers y reglas aprobadas | DEC-18 | `ZM-FIN-002`; tarea posterior de alertas/worker | `adminModules.ts`; `adminData.ts`; `AdminModulePage`; worker | Navegación, página, API y worker | No existe motor de alertas productivo |
| BO-PROD-01 | Backoffice | Productos | `/admin/productos` | Listar, detallar, crear y editar productos | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Candidata visible con RBAC/scope y validación | DEC-02 | `ZM-FIN-008`; `ZM-FIN-015`–`022`; tarea funcional posterior | `products/pages/AdminProductsPage.tsx`; `products/api.ts`; módulo catalog | Página, navegación y router API | Disponibilidad y pruebas dinámicas pendientes |
| BO-CLASS-01 | Backoffice | Categorías/clases | `/admin/categorias` | CRUD de clases | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Visible con RBAC/scope y reglas validadas | DEC-02 | `ZM-FIN-015`–`022`; validación funcional posterior | `classes/pages/AdminClassesPage.tsx`; `classes/api.ts`; product-classes API | Página y routers | Reglas PRODUCT_DIRECT/CLASS_CAPTURE pendientes de validación |
| BO-PRICE-01 | Backoffice | Precios | `/admin/precios` | Consultar y actualizar precio/costo | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Visible con permiso y política comercial aprobada | DEC-02 | `ZM-FIN-015`–`022`; tarea pricing posterior | `prices/pages/AdminPricesPage.tsx`; `prices/api.ts`; módulo pricing | Página, servicio y permisos | Vigencia y concurrencia dinámicas pendientes |
| BO-RECIPE-01 | Backoffice | Recetas/costos | `/admin/recetas-costos` | Crear, duplicar, activar, aplicar costo y editar versión | `PARCIAL` | `INCLUIDA_OCULTA_HASTA_COMPLETARSE` | Ocultar acciones incompletas hasta vertical terminada | DEC-02 | `ZM-FIN-002`; tarea funcional de recetas/producción | `recipes-costs/pages/AdminRecipeCostsPage.tsx`; `recipes-costs/api.ts` | Página, API y contratos | No hay edición completa de versión existente |
| BO-CDISC-01 | Backoffice | Descuentos comerciales | `/admin/descuentos` | Administrar y duplicar reglas comerciales | `REAL_INTEGRADA` | `INCLUIDA_OCULTA_HASTA_COMPLETARSE` | Ocultar hasta que las reglas tengan consumidor real | DEC-02 | `ZM-FIN-002`; tarea pricing/descuentos posterior | `discounts/pages/AdminDiscountsPage.tsx`; admin discounts API; `commercial_discounts` | Página admin y navegación | CRUD real sin efecto en venta |
| BO-CDISC-02 | API/POS | Descuentos comerciales | Venta o pedido | Resolver y aplicar promociones | `DESCONECTADA` | `INCLUIDA_OCULTA_HASTA_COMPLETARSE` | No habilitar administración como productiva hasta integrar consumidor | DEC-02 | Tarea pricing/descuentos posterior | Ausencia de consumidor en sales, orders y POS; módulo discounts | Sales/orders/discount service | Las reglas persistidas no afectan importes |
| BO-SALE-01 | Backoffice | Ventas/tickets | `/admin/ventas` | Consultar ventas y tickets | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Visible sólo con RBAC/scope | DEC-03, DEC-04 | `ZM-FIN-015`–`022`; validación funcional posterior | `sales-tickets/pages/AdminSalesTicketsPage.tsx`; `sales-tickets/api.ts` | Página, navegación y router | Permiso granular ausente |
| BO-SALE-02 | Backoffice | Tickets | Detalle | Reimprimir físicamente | `PARCIAL` | `INCLUIDA_OCULTA_HASTA_COMPLETARSE` | Ocultar hasta salida física demostrable | DEC-15, DEC-16 | `ZM-FIN-002`; tarea de impresión posterior | Endpoint reprint, página sales-tickets; ausencia de impresión equivalente al POS | Página de ventas y renderer/spool | La mutación de auditoría no demuestra impresión |
| BO-ORD-01 | Backoffice | Pedidos | `/admin/pedidos` | Consultar, preparar, entregar y cancelar | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Visible con RBAC/scope y reglas de pedidos validadas | DEC-02 | `ZM-FIN-015`–`022`; tarea de pedidos posterior | `orders/pages/AdminOrdersPage.tsx`; `orders/api.ts`; módulo orders | Página, navegación y routers | Comunicación al cliente separada |
| BO-RETCOR-01 | Backoffice | Devoluciones/correcciones | `/admin/devoluciones-correcciones` | Consultar documentos | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Sólo lectura y con RBAC/scope | DEC-02 | `ZM-FIN-015`–`022`; validación funcional posterior | `returns-corrections/pages/AdminReturnsCorrectionsPage.tsx`; API | Página, navegación y permisos | No implica aprobación de acciones POS |
| BO-BRANCH-01 | Backoffice | Sucursales/cajas | `/admin/sucursales`, `/admin/cajas-estaciones` | CRUD de sucursales y estaciones | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Visible sólo con RBAC y scopes efectivos | DEC-03, DEC-04, DEC-15 | `ZM-FIN-015`–`022`; validación funcional posterior | `branches/pages/AdminBranchesPage.tsx`; `workstations/pages/AdminWorkstationsPage.tsx`; APIs | Páginas, navegación y routers | Hardware físico separado; alias `/admin/cajas` duplicado |
| BO-INV-01 | Backoffice | Inventario | `/admin/inventario` | Consultar balances/movimientos y ajustar | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Visible con autorización alta, scope e integridad | DEC-02 | `ZM-FIN-015`–`022`; tareas de inventario posteriores | `inventory/pages/AdminInventoryPage.tsx`; `inventory/api.ts`; módulo inventory | Página, router y servicio | Concurrencia e integración de todos los flujos pendientes |
| BO-TRF-01 | Backoffice | Transferencias | `/admin/transferencias` | Crear, editar, despachar, recibir y cancelar | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Visible con RBAC/scope, idempotencia y ledger | DEC-02 | `ZM-FIN-015`–`022`; tareas logísticas posteriores | `transfers/pages/AdminTransfersPage.tsx`; `transfers/api.ts`; módulo transfers | Página, routers y servicio | Atomicidad no ejecutada |
| BO-PRD-01 | Backoffice | Producción | `/admin/produccion` | Crear, editar, iniciar, completar y cancelar | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Visible con RBAC/scope y semántica de producción aprobada | DEC-02 | `ZM-FIN-015`–`022`; tareas de producción posteriores | `production/pages/AdminProductionPage.tsx`; `production/api.ts`; módulo production | Página, routers y servicio | Variancias, consumos y concurrencia pendientes |
| BO-WASTE-01 | Backoffice | Merma | `/admin/merma` | Consultar, detallar y crear merma | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Visible con RBAC/scope y política de merma | DEC-02 | `ZM-FIN-015`–`022`; tareas de merma posteriores | `waste/pages/AdminWastePage.tsx`; `waste/api.ts`; módulo waste | Página, router y servicio | Aprobación de alto impacto pendiente |
| BO-SUP-01 | Backoffice | Proveedores | `/admin/proveedores` | CRUD y estado principal | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Visible con RBAC/scope | DEC-03, DEC-04 | `ZM-FIN-015`–`022`; validación funcional posterior | `suppliers/pages/AdminSuppliersPage.tsx`; `suppliers/api.ts`; módulo suppliers | Página, navegación y router | Relaciones se clasifican por separado |
| BO-SUP-02 | API | Proveedores | Sin acción UI | Administrar contactos, productos y sucursales del proveedor | `BACKEND_SIN_SUPERFICIE` | `INCLUIDA_OCULTA_HASTA_COMPLETARSE` | No exponer como funcional hasta añadir acciones | DEC-03, DEC-04 | `ZM-FIN-002`; tarea funcional posterior | Backend y API client de suppliers; página no los invoca | Detalle y acciones supplier | Backend productivo sin superficie de usuario |
| BO-PUR-01 | Backoffice | Compras | `/admin/compras-entradas` | Crear, entrada directa, confirmar, recibir y cancelar | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Visible con RBAC/scope e inventario validado | DEC-02 | `ZM-FIN-015`–`022`; tareas de compras posteriores | `purchases/pages/AdminPurchasesPage.tsx`; `purchases/api.ts`; módulo purchases | Página, router y servicio | Alias `/admin/compras`; flujo dinámico pendiente |
| BO-PUR-02 | API | Compras | Sin acción UI | Editar borrador | `BACKEND_SIN_SUPERFICIE` | `INCLUIDA_OCULTA_HASTA_COMPLETARSE` | No presentar CRUD completo hasta añadir UI o resolver alcance | DEC-03, DEC-04 | `ZM-FIN-002`; tarea funcional posterior | Backend PATCH purchase; ausencia de acción/página | Purchases API/page | Operación backend sin cliente de usuario |
| BO-INP-01 | Backoffice | Insumos | `/admin/insumos-consumibles` | CRUD y estado de insumos | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Visible con RBAC/scope y semántica de inventario | DEC-02 | `ZM-FIN-015`–`022`; tareas funcionales posteriores | `inputs-supplies/pages/AdminInputsSuppliesPage.tsx`; API | Página, router y servicio | Relaciones de proveedor separadas |
| BO-INP-02 | API | Insumos | Sin acción UI | Asociar proveedor a insumo | `BACKEND_SIN_SUPERFICIE` | `INCLUIDA_OCULTA_HASTA_COMPLETARSE` | Ocultar hasta añadir detalle y acción | DEC-03, DEC-04 | `ZM-FIN-002`; tarea funcional posterior | `inputs-supplies/api.ts`; backend relation; página no consume | Inputs page/API | Relación productiva sin superficie |
| BO-CASHREAD-01 | Backoffice | Caja | `/admin/cortes-caja`, `/admin/flujo-efectivo` | Consultar cortes y movimientos | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Visible con RBAC/scope y reconciliación validada | DEC-02 | `ZM-FIN-015`–`022`; tareas financieras posteriores | `cash-cuts/pages/AdminCashCutsPage.tsx`; `cash-flow/pages/AdminCashFlowPage.tsx`; APIs | Páginas, permisos y route hints | Un route hint usa alias antiguo de ventas |
| BO-REC-01 | Backoffice | Conciliación | `/admin/conciliacion` | Crear y resolver conciliación | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Visible con autorización alta y reglas financieras | DEC-02 | `ZM-FIN-015`–`022`; tareas financieras posteriores | `reconciliation/pages/AdminReconciliationPage.tsx`; API | Página, router y servicio | Proveedor bancario no integrado; evidencia manual |
| BO-OPPAY-01 | Backoffice | Pagos operativos | `/admin/pagos-operativos` | Administrar o revisar pagos operativos | `PLACEHOLDER` | `INCLUIDA_OCULTA_HASTA_COMPLETARSE` | Ocultar o sustituir por superficie real | DEC-03, DEC-04, DEC-18 | `ZM-FIN-002`; tarea funcional posterior | `adminModules.ts`; `adminData.ts`; `AdminModulePage` | Navegación, página y fuente de datos | Shell desconectado aunque POS/cash flow tengan datos reales |
| BO-CLN-01 | Backoffice | Limpieza | `/admin/bitacoras-limpieza` | Listar, crear, completar y cancelar | `PARCIAL` | `INCLUIDA_OCULTA_HASTA_COMPLETARSE` | Ocultar acción/ciclo incompleto | DEC-03, DEC-04 | `ZM-FIN-002`; tarea funcional posterior | `cleaning-logs/pages/AdminCleaningLogsPage.tsx`; API | Página y acciones | Página no consume cancelación soportada por backend/client |
| BO-SAN-01 | Backoffice | Verificación sanitaria | `/admin/verificaciones-sanitarias` | Crear, iniciar, completar y cancelar | `PARCIAL` | `INCLUIDA_OCULTA_HASTA_COMPLETARSE` | Ocultar acción/ciclo incompleto | DEC-03, DEC-04, DEC-16 | `ZM-FIN-002`; tarea funcional posterior | `sanitary-verifications/pages/AdminSanitaryVerificationsPage.tsx`; API | Página y acciones | Cancelación no expuesta |
| BO-INC-01 | Backoffice | Incidencias | `/admin/incidencias` | Crear primer registro, seguimiento, estado, resolver y reabrir | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Visible con RBAC/scope y validación | DEC-03, DEC-04 | `ZM-FIN-015`–`022`; validación funcional posterior | `incidents/pages/AdminIncidentsPage.tsx`; `incidents/api.ts`; módulo quality | Página, permisos y routers | El problema histórico de primer registro no aparece estáticamente |
| BO-EQP-01 | Backoffice | Equipos | `/admin/equipos-mantenimiento` | Crear equipo, cambiar estado y gestionar mantenimiento principal | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Visible con RBAC/scope y validación | DEC-03, DEC-04, DEC-15 | `ZM-FIN-015`–`022`; validación funcional posterior | `equipment-maintenance/pages/AdminEquipmentMaintenancePage.tsx`; API | Página, permisos y routers | El problema histórico de primer registro no aparece estáticamente |
| BO-EQP-02 | API | Equipos | Sin acción UI | Editar equipo y cancelar mantenimiento | `BACKEND_SIN_SUPERFICIE` | `INCLUIDA_OCULTA_HASTA_COMPLETARSE` | Ocultar hasta añadir acciones | DEC-03, DEC-04 | `ZM-FIN-002`; tarea funcional posterior | Backend equipment update/cancel; página sin acciones | Equipment page/API | Backend sin superficie equivalente |
| BO-USR-01 | Backoffice | Usuarios | `/admin/usuarios` | Crear, editar, cambiar estado, bloquear y asignar sucursal | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Visible sólo tras RBAC/scopes deny-by-default | DEC-03, DEC-04, DEC-05 | `ZM-FIN-015`–`022` | `users/pages/AdminUsersPage.tsx`; `users/api.ts`; módulo identity | Página, navegación y routers | Enforcement efectivo separado |
| BO-USR-02 | API | Usuarios | Sin acción UI clara | Desactivar/default de asignaciones y operaciones auxiliares | `BACKEND_SIN_SUPERFICIE` | `INCLUIDA_OCULTA_HASTA_COMPLETARSE` | Ocultar hasta añadir acciones inequívocas | DEC-03, DEC-04 | `ZM-FIN-015`–`022`; tarea funcional posterior | Backend/API de branch assignments; uso parcial en página | Users page/API | Granularidad exacta debe documentarse en `ZM-FIN-008` |
| BO-ROLE-01 | Backoffice | Roles/permisos | `/admin/roles-permisos` | CRUD roles, catálogo y asignación de usuarios | `REAL_INTEGRADA` | `INCLUIDA_OCULTA_HASTA_COMPLETARSE` | Ocultar hasta enforcement y separación de funciones | DEC-03, DEC-04 | `ZM-FIN-015`–`022` | `roles-permissions/pages/AdminRolesPermissionsPage.tsx`; API; modelos identity | Página, navegación, routers y policy engine | Administración real no implica aplicación efectiva |
| BO-ROLE-02 | Backoffice/API | Autorización | Todas `/admin/*` | Aplicar grants module/action/scope | `DESCONECTADA` | `INCLUIDA_OCULTA_HASTA_COMPLETARSE` | Deny-by-default antes de mostrar módulos sensibles | DEC-03, DEC-04 | `ZM-FIN-015`–`022`; documentación detallada en `ZM-FIN-008` | TODO de `AdminLayout`; gates `_require_backoffice_user` | Layout, navigation y routers administrativos | Todo usuario Backoffice ve navegación completa |
| BO-AUD-01 | Backoffice | Auditoría | `/admin/auditoria` | Listar, detallar y exportar eventos | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Visible sólo con RBAC/scope e integridad verificadas | DEC-03, DEC-04, DEC-16 | `ZM-FIN-015`–`022`; validación funcional posterior | `audit/pages/AdminAuditPage.tsx`; `audit/api.ts`; `audit_log` | Página, permisos y export | Inmutabilidad/retención dinámicas pendientes |
| BO-RPT-01 | Backoffice | Reportes | `/admin/reportes` | Ejecutar ocho previews y exportar JSON | `REAL_INTEGRADA` | `INCLUIDA_VISIBLE_PENDIENTE_VALIDACION` | Visible sólo con RBAC/scope y definiciones aprobadas | DEC-03, DEC-04, DEC-16, DEC-18 | `ZM-FIN-015`–`022`; tareas de reportes posteriores | `reports/pages/AdminReportsPage.tsx`; reports service; ocho definiciones AVAILABLE | Página, permisos, export y servicio | Permisos son metadata; único formato JSON |
| BO-RPT-02 | Backoffice | Reportes | `/admin/reportes` | Compras-proveedor, salud de catálogo y auditoría resumida | `PLACEHOLDER` | `INCLUIDA_OCULTA_HASTA_COMPLETARSE` | Ocultar o mostrar inequívocamente pendiente | DEC-16, DEC-18 | `ZM-FIN-002`; tarea de reportes posterior | Tres definiciones `REQUIRES_BACKEND`; sin generator/export | Reports page/service | Tres reportes incompletos |
| BO-SET-01 | Backoffice | Configuración | `/admin/configuracion` | Listar, editar, resetear e historiar 33 claves | `REAL_INTEGRADA` | `INCLUIDA_OCULTA_HASTA_COMPLETARSE` | Ocultar controles sin efecto demostrable | DEC-03, DEC-04; decisión temática por clave | `ZM-FIN-002`; tareas funcionales posteriores | `settings/pages/AdminSettingsPage.tsx`; `settings/api.ts`; system_settings/history | Página, navegación y config service | Persistencia real no implica efecto operacional |
| BO-SET-02 | API/producto | Configuración | Flujos operativos | Consumir overrides persistidos | `DESCONECTADA` | `INCLUIDA_OCULTA_HASTA_COMPLETARSE` | No mostrar configuración como efectiva hasta integrarla | DEC-02 | Tareas funcionales posteriores | `SystemSetting` sólo consumido por servicio administrativo de configuración | Servicios de negocio, POS y Backoffice | Cambiar una clave puede no cambiar la operación |
| SYS-HEALTH-01 | API | Health | `/health` | Sonda operativa | `REAL_INTEGRADA` | `EXCLUIDA_OBSOLETA_DUPLICADA_O_INTERNA` | Conservar como control técnico; no incluir en catálogo de usuario | DEC-17, DEC-18 | Tarea de infraestructura/observabilidad posterior | `apps/api/src/zeromerma_api/presentation/health.py`; router API | Health/readiness y proxy | Excluida sólo como función de usuario, no eliminada |
| SYS-HEALTH-02 | Webs | Demo/home | `/health`; Backoffice `/` | Demo health y shell público | `INTERNA_DESARROLLO` | `EXCLUIDA_OBSOLETA_DUPLICADA_O_INTERNA` | Retirar de navegación productiva | DEC-17, DEC-18 | `ZM-FIN-002`; tarea de infraestructura posterior | Routers POS/Backoffice; `HealthDemoPage`; `HomePage` | Ambos routers | API health sí debe conservarse técnicamente |
| SYS-DEVAUD-01 | API | Auditoría de desarrollo | `/dev/audit/snapshot` | Snapshot técnico | `INTERNA_DESARROLLO` | `EXCLUIDA_OBSOLETA_DUPLICADA_O_INTERNA` | Desactivado y no expuesto como producto | DEC-03, DEC-04, DEC-17 | Tareas de seguridad/infraestructura posteriores | Módulo `dev_audit`; `include_in_schema=False`; flag/token | Router y configuración dev | Explica diferencia entre operaciones de código y OpenAPI |
| SYS-WRK-01 | Worker | Outbox | Proceso worker | Reservar y leer lote | `PARCIAL` | `INCLUIDA_OCULTA_HASTA_COMPLETARSE` | No declarar worker operativo | DEC-02 | Tarea posterior de outbox/worker | `apps/worker/src/zeromerma_worker/outbox/poller.py`; `OutboxPoller` | Poller, readiness y métricas | Lee eventos pero no los procesa |
| SYS-WRK-02 | Worker | Handlers | Eventos | Procesar, reintentar y finalizar eventos | `DESCONECTADA` | `INCLUIDA_OCULTA_HASTA_COMPLETARSE` | No habilitar efectos delegados al worker | DEC-02 | Tarea posterior de outbox/worker | Cero handlers/jobs; no actualiza `processed_at` ni intentos | Worker handlers, outbox y observabilidad | Alertas/notificaciones no pueden entregarse |
| SYS-TRAIN-01 | Plataforma | Training | Flag, banner y DB separada | Modo de entrenamiento | `INTERNA_DESARROLLO` | `EXCLUIDA_OBSOLETA_DUPLICADA_O_INTERNA` | Nunca habilitar en producción; conservar soporte no productivo aislado | DEC-17 | Tarea de infraestructura posterior | `docs/implementation/training-mode.md`; API flag; `training-mode-banner.tsx` | Configuración, despliegue y banner | Requiere entorno y DB separados |
| SYS-DEVTOOLS-01 | Repositorio | Scripts | CLI | Seeds, reset local, generación y prompts | `INTERNA_DESARROLLO` | `EXCLUIDA_OBSOLETA_DUPLICADA_O_INTERNA` | Restringir a desarrollo | DEC-17 | `ZM-FIN-004`–`006`; tareas de infraestructura posteriores | Scripts del workspace; `scripts/`; `docs/codex` | Scripts y configuración de entorno | No son capacidades de usuario |
| SYS-FISCAL-01 | Plataforma | Fiscalidad | Sin superficie canónica | Facturación, timbrado e impuestos jurisdiccionales | `PLACEHOLDER` | `INCLUIDA_BLOQUEADA_POR_DECISION` | No declarar cumplimiento ni habilitar emisión | DEC-16 | Tarea posterior de requisitos externos | Campos fiscales parciales en compras/config; ausencia de emisión | Dominio fiscal, provider y UI por definir | Jurisdicción y obligaciones desconocidas |
| SYS-PRIV-01 | Plataforma | Privacidad | Contactos/comunicaciones | Consentimiento, retención y derechos | `NO_VERIFICABLE_ESTATICAMENTE` | `INCLUIDA_BLOQUEADA_POR_DECISION` | Bloquear comunicaciones y tratamientos no aprobados | DEC-16 | Tarea posterior de requisitos externos | Contactos existentes; ausencia de política canónica localizable | Identity, orders, communication y export | Depende de jurisdicción y uso real |
| SYS-INFRA-01 | Plataforma | Producción | Despliegue | Hosting, backups, restore, observabilidad y DR | `PLACEHOLDER` | `INCLUIDA_BLOQUEADA_POR_DECISION` | No declarar production ready | DEC-17 | Tareas de infraestructura/continuidad posteriores | Infra local y documentación parcial; sin plataforma productiva cerrada | Infra, config, secrets, docs y pipelines | Proveedor, RPO/RTO y restore pendientes |
| SYS-ALIAS-01 | Backoffice | Compatibilidad | `/admin/roles`, `/admin/cajas`, `/admin/ventas-tickets`, `/admin/compras` | Redirigir aliases antiguos | `REAL_INTEGRADA` | `EXCLUIDA_OBSOLETA_DUPLICADA_O_INTERNA` | No son rutas canónicas; mantener sólo durante migración controlada | DEC-02 | `ZM-FIN-002`; tarea posterior de limpieza de referencias | `apps/backoffice-web/src/router.tsx`; route hints y tests | Router, referencias, pruebas y enlaces | Un route hint todavía usa `/admin/ventas-tickets` |

## DEC-03 — RBAC

- **Estado:** `APROBADA`
- **Fecha:** 2026-08-27
- **Propietario:** propietario de ZeroMerma
- **Contenido aprobado:** autorización backend deny-by-default, catálogo canónico de capacidades, Superadministrador explícito, separación de funciones y procedimiento excepcional con un único Superadministrador.
- **Respuesta aprobada:** política normativa, catálogo de 55 capacidades y CLI local break-glass descritos en esta decisión.

### Política normativa aprobada

1. ZeroMerma utilizará autorización backend `deny-by-default`.
2. Tener acceso a Backoffice no concede por sí mismo autoridad administrativa.
3. Toda operación protegida deberá declarar una capacidad backend explícita.
4. La UI sólo reflejará grants efectivos para UX; nunca será autoridad de seguridad.
5. Existirá un rol explícito de Superadministrador.
6. El Superadministrador no se inferirá por email, usuario seed, `allowed_surfaces` ni ausencia de scope.
7. El rol canónico será explícitamente identificable como Superadministrador y tendrá `GLOBAL` explícito.
8. No habrá wildcard implícito de capacidades: el Superadministrador sólo obtendrá capacidades explícitamente asignadas al rol.
9. Una capacidad nueva no será concedida automáticamente al Superadministrador hasta incorporarla deliberadamente al rol.
10. Habrá separación entre administración de usuarios, administración de roles/capacidades y asignación de roles/scopes.
11. `users.manage` no permitirá conceder privilegios.
12. `roles.manage` no permitirá autoelevación ni asignar unilateralmente Superadministrador.
13. `role_assignments.manage` administrará asignaciones ordinarias, pero no eludirá las reglas especiales de Superadministrador.
14. Ningún actor podrá autoasignarse privilegios superiores.
15. No podrá eliminarse, bloquearse, desactivarse, degradarse, quitarse Backoffice ni reducirse a scope no global al último Superadministrador activo.
16. Las comprobaciones del último Superadministrador deberán serializarse transaccionalmente para impedir que cambios concurrentes eliminen la última autoridad.
17. Cuando existan al menos dos Superadministradores activos, todo cambio de privilegio de Superadministrador requerirá iniciador Superadministrador, aprobador Superadministrador distinto, aprobación durable, payload exacto aprobado, expiración, uso único, revalidación de ambos actores al ejecutar, auditoría y outbox.
18. Cuando exista únicamente un Superadministrador activo, el procedimiento canónico excepcional será una **CLI local break-glass dedicada**.
19. La CLI local break-glass:
    - sólo podrá ejecutarse desde un host o control plane autorizado;
    - requerirá material de recuperación independiente y de un solo uso;
    - reutilizará el servicio de aplicación y sus invariantes;
    - no ejecutará SQL manual como mecanismo normal;
    - sólo podrá crear o promover al segundo Superadministrador;
    - no podrá degradar, desactivar ni eliminar al último Superadministrador;
    - serializará la operación;
    - generará auditoría y outbox transaccionales;
    - invalidará o rotará el material de recuperación utilizado.
20. Un endpoint web break-glass no será el mecanismo canónico aprobado.
21. SQL o migraciones manuales no serán el procedimiento operativo normal de recuperación; sólo podrán formar parte de disaster recovery extraordinario fuera de esta política.

### Catálogo técnico canónico

El catálogo canónico derivado de la política aprobada contiene exactamente estos 55 códigos únicos:

```text
pos.operate
sales_tickets.view
sales_tickets.reprint
orders.view
orders.manage
orders.cancel
returns_corrections.view
returns_corrections.manage
catalog.view
catalog.manage
catalog.availability.manage
pricing.view
pricing.manage
recipes.view
recipes.manage
discounts.view
discounts.manage
inventory.view
inventory.adjust
branches.view
branches.manage
workstations.view
workstations.manage
transfers.view
transfers.manage
transfers.execute
transfers.cancel
production.view
production.manage
production.execute
production.cancel
waste.view
waste.manage
suppliers.view
suppliers.manage
purchases.view
purchases.manage
purchases.confirm
purchases.receive
purchases.cancel
cash_finance.view
cash_finance.manage
quality_hygiene.view
quality_hygiene.manage
users.view
users.manage
roles.view
roles.manage
role_assignments.manage
audit.view
audit.export
reports.view
reports.export
config.view
config.manage
```

### Capacidades existentes a retirar después de migración

Las siguientes capacidades quedan deprecadas conceptualmente una vez que todos sus consumidores hayan migrado. No deben eliminarse antes de completar esa migración:

```text
catalog_products.manage
multibranch_operations.manage
purchases_supply.manage
```

No se mantendrá una arquitectura paralela ni una capa permanente de aliases para estas capacidades.

### Reglas de separación relevantes

Las siguientes capacidades son autoridades diferentes y no se implican entre sí:

```text
users.view != users.manage
roles.view != roles.manage
roles.manage != role_assignments.manage
inventory.view != inventory.adjust
reports.view != reports.export
audit.view != audit.export
sales_tickets.view != sales_tickets.reprint
```

La misma regla de mínimo privilegio se aplicará a los splits restantes: lectura, mantenimiento ordinario, ejecución, aprobación, cancelación, reversa y exportación no se combinarán cuando hacerlo impida expresar la separación de funciones aprobada.

### Evidencia, tareas, consecuencias e historial

- **Evidencia:** validación técnica de `ZM-FIN-003`; catálogo vigente de 17 capacidades en `apps/api/src/zeromerma_api/modules/identity/application/permissions.py`; ausencia de enforcement backend por capacidad; modelos `Role`, `Permission`, `RolePermission`, `UserRoleAssignment` y `UserBranchAssignment`; guardas actuales basadas en superficie o `roles.manage`; ausencia de un mecanismo productivo break-glass.
- **Tareas afectadas:** `ZM-FIN-003`, `ZM-FIN-008`, `ZM-FIN-015`, `ZM-FIN-016`, `ZM-FIN-017`, `ZM-FIN-018`, `ZM-FIN-019`, `ZM-FIN-020`, `ZM-FIN-021` y `ZM-FIN-022`.
- **Consecuencias:** los routers deberán aplicar capacidades explícitas en backend; usuarios, roles y asignaciones tendrán autoridades separadas; Superadministrador, doble intervención y break-glass requerirán implementación, migraciones y pruebas específicas.
- **Límite:** DEC-03 define la política normativa y el catálogo; no certifica que RBAC, Superadministrador o la CLI break-glass estén implementados, migrados o probados.
- **Historial:** `PENDIENTE` desde 2026-08-26; `APROBADA` por el propietario el 2026-08-27, incluida la opción A de CLI local break-glass dedicada.

## DEC-04 — Scopes

- **Estado:** `APROBADA`
- **Fecha:** 2026-08-27
- **Propietario:** propietario de ZeroMerma
- **Contenido aprobado:** scopes explícitos `GLOBAL` y `BRANCH_SET`, resolución por capacidad, intersección con sucursales asignadas, reglas multisucursal y modelo técnico normalizado.
- **Respuesta aprobada:** política normativa, modelo y algoritmo descritos en esta decisión.

### Política normativa aprobada

1. ZeroMerma soportará usuarios Backoffice con múltiples sucursales y operaciones administrativas centralizadas.
2. Todo scope será explícito: `GLOBAL` o `BRANCH_SET`.
3. Scope ausente o vacío nunca significará `GLOBAL`.
4. Los grants se resolverán por capacidad.
5. Varias asignaciones activas que concedan la misma capacidad podrán aportar scopes.
6. Los scopes de esas asignaciones se unirán por capacidad.
7. Para asignaciones `BRANCH_SET`, el scope autorizado se intersectará con las `UserBranchAssignment` activas del usuario.
8. Una sucursal no activamente asignada al usuario no podrá utilizarse mediante `BRANCH_SET`, aunque aparezca en el scope del rol.
9. `GLOBAL` explícito no será limitado por `UserBranchAssignment`.
10. `GLOBAL` nunca se inferirá de ausencia de scope, pertenencia a Backoffice, rol seed, email ni múltiples sucursales.
11. El Superadministrador tendrá `GLOBAL` explícito.
12. Una operación origen-destino requerirá autoridad sobre ambos extremos, salvo `GLOBAL`.
13. Los listados sin filtro de sucursal no ampliarán acceso: con `BRANCH_SET`, el backend inyectará el conjunto efectivo; con `GLOBAL`, podrá consultar globalmente conforme a la capacidad.
14. Agregados, reportes y exportaciones sólo incluirán sucursales autorizadas.
15. Una sucursal inactiva no permitirá operaciones económicas ordinarias.
16. Ningún usuario o rol existente será convertido silenciosamente a `GLOBAL` durante una migración.

### Modelo técnico canónico

El modelo normalizado derivado de DEC-04 será:

```text
UserRoleAssignment
  scope_type: GLOBAL | BRANCH_SET, obligatorio

UserRoleAssignmentBranchScope
  assignment_id FK
  branch_id FK
  UNIQUE(assignment_id, branch_id)
```

Invariantes:

```text
GLOBAL -> cero filas branch scope
BRANCH_SET -> al menos una fila branch scope
scope ausente -> inválido y DENY
```

La relación actual `(user_id, role_id)` puede conservarse: una única asignación usuario-rol contiene el conjunto completo de sucursales de esa asignación. La implementación deberá preservar integridad referencial mediante FKs y validación transaccional. JSON o ARRAY no será el modelo canónico de scope.

### Algoritmo normativo

```text
1. usuario inexistente, inactivo o bloqueado -> DENY
2. capacidad inexistente o inactiva -> DENY
3. considerar sólo roles, asignaciones y permisos activos
4. ausencia de grant -> DENY
5. unir scopes de todas las asignaciones que conceden ESA capacidad
6. GLOBAL explícito -> ALLOW_GLOBAL
7. BRANCH_SET -> unión de scopes de rol
8. intersectar BRANCH_SET con UserBranchAssignment activas
9. scope efectivo vacío -> DENY
10. colección sin filtro -> servidor limita al scope efectivo
11. origen-destino -> ambos deben pertenecer al scope efectivo
12. Superadministrador requiere GLOBAL explícito y RolePermission explícito
```

### Ejemplos normativos

1. `sales_tickets.view` en Norte permite consultar Norte y niega Centro.
2. `sales_tickets.view` en Norte y Centro junto con `inventory.adjust` sólo en Norte no comparte scopes entre capacidades: el ajuste en Centro se deniega.
3. Una transferencia Norte-Sur requiere autoridad sobre Norte y Sur; disponer sólo de Norte produce `DENY`, mientras que `GLOBAL` explícito permite ambos extremos.
4. Dos roles que conceden la misma capacidad en Norte y Centro producen la unión Norte más Centro antes de aplicar la frontera del usuario.
5. Un rol que concede Norte y Centro, combinado con `UserBranchAssignment` activa sólo en Norte, produce scope efectivo Norte.
6. Un Superadministrador con `GLOBAL` explícito obtiene `ALLOW_GLOBAL`, pero sólo para capacidades asignadas explícitamente mediante `RolePermission`.

### Migración conceptual

- El rol `admin` actual no se convertirá automáticamente en Superadministrador ni recibirá automáticamente `GLOBAL`.
- `cashier` migrará a `BRANCH_SET` con sus sucursales activas.
- `branch_manager` migrará a `BRANCH_SET` con sus sucursales activas.
- Los roles personalizados se traducirán a las nuevas capacidades; una combinación ambigua quedará pendiente o inactiva hasta revisión.
- La ausencia de una sucursal asignada no producirá `GLOBAL`.
- La selección del primer Superadministrador y de los administradores que realmente requieran `GLOBAL` dependerá de la inspección de datos existentes en DEC-19.

### Evidencia, tareas, consecuencias e historial

- **Evidencia:** validación técnica de `ZM-FIN-003`; modelos actuales `User`, `UserBranchAssignment`, `Role`, `Permission`, `RolePermission` y `UserRoleAssignment`; contrato `AdminRoleScopeView` con soporte deshabilitado; ausencia actual de scope persistido.
- **Tareas afectadas:** `ZM-FIN-003`, `ZM-FIN-008`, `ZM-FIN-015`, `ZM-FIN-016`, `ZM-FIN-017`, `ZM-FIN-018`, `ZM-FIN-019`, `ZM-FIN-020`, `ZM-FIN-021` y `ZM-FIN-022`.
- **Consecuencias:** scopes normalizados y obligatorios, filtros backend por scope efectivo, autorización conjunta de origen y destino, migración sin globalización silenciosa y pruebas de aislamiento por sucursal.
- **Límite:** DEC-04 define la semántica y el modelo canónico; no certifica que scopes, filtros o migraciones estén implementados o probados.
- **Historial:** `PENDIENTE` desde 2026-08-26; `APROBADA` por el propietario el 2026-08-27.

## DEC-05 — Sesión

- **Estado:** `APROBADA`
- **Fecha:** 2026-08-27
- **Propietario:** propietario de ZeroMerma
- **Contenido aprobado:** sesiones opacas server-side independientes para POS y Backoffice; cookies seguras; protección CSRF; expiración, bloqueo y revocación; vínculo explícito con estación y caja; y migración sin convivencia permanente con bearer.
- **Respuesta aprobada:** política normativa, modelo conceptual y estrategia de migración descritos en esta decisión.

### Arquitectura de sesión

1. POS y Backoffice utilizarán sesiones opacas persistidas server-side.
2. POS y Backoffice tendrán audiencias y sesiones independientes.
3. La credencial será un secreto aleatorio criptográficamente fuerte y opaco.
4. El secreto crudo nunca se persistirá server-side; se almacenará únicamente un hash o HMAC adecuado para verificarlo.
5. La credencial se transportará únicamente mediante cookie segura.
6. No habrá bearer en URL, bearer persistido en `localStorage`, sesión compartida POS-Backoffice, SSO implícito ni canje automático POS-Backoffice.
7. POS-Backoffice continuará requiriendo login Backoffice independiente.
8. Los grants y scopes no se almacenarán como autoridad dentro de la cookie; se resolverán server-side conforme a DEC-03 y DEC-04.

### Modelo canónico de sesión

La entidad conceptual común será equivalente a:

```text
AuthSession
  id
  credential_hash
  user_id
  audience: POS | BACKOFFICE
  status: ACTIVE | LOCKED | REVOKED | EXPIRED
  created_at
  last_activity_at
  idle_expires_at
  absolute_expires_at
  revoked_at nullable
  revocation_reason nullable
  workstation_id nullable
  cash_session_id nullable
```

Invariantes:

- Para `POS`, `workstation_id` será obligatorio y `cash_session_id` será opcional para representar el vínculo con el turno cuando exista.
- Para `BACKOFFICE`, `workstation_id` y `cash_session_id` serán nulos.
- `AuthSession`, `CashSession` y `Workstation` son entidades distintas y no deberán fusionarse.
- IP y user-agent serán datos opcionales cuya necesidad y retención dependerán de DEC-16.
- Nunca se registrarán en auditoría el secreto de cookie, bearer heredado, token o secreto CSRF, contraseña ni material break-glass. El estado de sesión conservará únicamente verificadores no reversibles, como `credential_hash` y el verificador necesario para el token CSRF synchronizer; nunca los secretos crudos.

### Cookies

La cookie POS tendrá como nombre recomendado `__Host-zm-pos-session`, `Secure=true`, `HttpOnly=true`, `Path=/`, `Domain` omitido y duración absoluta máxima de 12 horas.

La cookie Backoffice tendrá como nombre recomendado `__Host-zm-backoffice-session`, `Secure=true`, `HttpOnly=true`, `Path=/`, `Domain` omitido y duración absoluta máxima de 8 horas.

El valor de `SameSite` dependerá de la topología:

- despliegue same-site: `Lax` preferido;
- despliegue cross-site: `None; Secure` sólo cuando sea técnicamente necesario.

El valor final de `SameSite`, los orígenes productivos, TLS y reverse proxy dependen de DEC-17 y no alteran la política de negocio de DEC-05. La expiración del navegador nunca sustituirá la validación server-side. DEC-05 no aprueba un refresh token.

### CSRF y CORS

La autenticación mediante cookie requerirá protección CSRF en las mutaciones:

1. token CSRF synchronizer ligado server-side a la sesión;
2. conservación del token por el frontend únicamente en memoria;
3. envío mediante `X-CSRF-Token` en mutaciones;
4. validación backend del token y de `Origin`;
5. uso de `Referer` sólo como fallback documentado;
6. `SameSite` como defensa adicional, no como sustituto de CSRF;
7. CORS con credenciales limitado a orígenes productivos explícitos;
8. prohibición de `*` como origen credentialed productivo.

La topología concreta se resolverá posteriormente conforme a DEC-17.

### POS — idle y bloqueo

- El timeout de inactividad POS será de 5 minutos.
- La duración absoluta máxima POS será de 12 horas.
- El servidor será la autoridad del timeout.
- Polling, refetch automático, health checks y timers no contarán como actividad del operador.
- La actividad podrá transmitirse mediante heartbeat limitado y ligado a eventos reales de teclado, touch o pointer.
- Las mutaciones iniciadas por el usuario contarán como actividad.
- La actividad nunca extenderá la duración absoluta.
- Tras 5 minutos de inactividad, la sesión pasará de `ACTIVE` a `LOCKED`.
- Mientras esté `LOCKED`, no se permitirán operaciones de negocio; sólo estado de sesión, reautenticación y logout.
- El bloqueo no cerrará `CashSession` ni generará un cierre de turno.
- Una reautenticación correcta conservará la misma `AuthSession`, la devolverá a `ACTIVE`, rotará el secreto de cookie y no reiniciará el límite absoluto.
- Al alcanzar el máximo absoluto, `ACTIVE` o `LOCKED` pasará a `EXPIRED` y se exigirá un login completo.
- El código de dominio recomendado será `SESSION_LOCKED`; HTTP `423` podrá representar una sesión POS bloqueada.

### Unicidad POS

Existirá como máximo una `AuthSession` POS `ACTIVE` o `LOCKED` por combinación usuario y workstation.

- Un mismo usuario podrá autenticarse en estaciones diferentes mediante sesiones separadas y auditables.
- Dos browsers del mismo usuario en la misma estación no mantendrán dos slots activos.
- Una autenticación válida nueva reemplazará atómicamente la sesión anterior del mismo usuario y estación; la anterior quedará revocada con razón `REPLACED`.
- Una estación inactiva no podrá crear ni desbloquear una sesión.
- Autenticarse no concederá autoridad sobre una caja perteneciente a otro usuario.
- La restricción vigente de `CashSession OPEN` por usuario no se modifica mediante DEC-05 y deberá reconciliarse con DEC-06.

### Backoffice — sesiones múltiples

- El timeout de inactividad Backoffice será de 15 minutos.
- La duración absoluta máxima Backoffice será de 8 horas.
- Se permitirán múltiples sesiones Backoffice simultáneas por usuario.
- Cada sesión será visible al propio usuario, revocable individualmente e identificable mediante datos no secretos de creación, última actividad, expiración y estado.
- Se requerirán operaciones conceptuales para listar sesiones propias, revocar una sesión propia, revocar todas excepto la actual y hacer logout de la sesión actual.
- Administrar sesiones de otro usuario será autoridad derivada de `users.manage`, deberá respetar DEC-04 y no añadirá una capacidad nueva a DEC-03.

### Revocación

Una sesión afectada será inválida para cualquier request posterior al commit de su revocación.

Se revocarán inmediatamente las sesiones afectadas por logout, bloqueo o desactivación del usuario, cambio de contraseña, cambio de privilegios o scope, cambio de `UserBranchAssignment`, activación o desactivación de rol o permiso y modificación de `allowed_surfaces`.

Los cambios de autorización combinarán:

1. resolución de grants y scopes en cada request conforme a DEC-03 y DEC-04;
2. revocación de las sesiones de los usuarios afectados dentro de la misma transacción del cambio.

Los grants efectivos no se cachearán en la cookie como autoridad. Las operaciones sensibles en curso deberán revalidar autoridad antes de commit cuando la tarea funcional correspondiente lo exija.

### Cierre de caja y sesión POS

Cuando `CashSession` pase de `OPEN` a `CLOSED`, se revocarán dentro de la misma unidad transaccional todas las `AuthSession` POS `ACTIVE` o `LOCKED` cuyo `cash_session_id` corresponda a la caja cerrada, con razón `CASH_SESSION_CLOSED`.

Esto no significa revocar todas las sesiones del usuario, todas las sesiones de la estación ni únicamente la sesión del navegador que ejecutó el cierre. La definición de carreras entre venta, pago y cierre pertenece a DEC-06.

### Cambio y recuperación de contraseña

- El cambio propio de contraseña revocará todas las sesiones, incluida la actual.
- Un reset administrativo revocará todas las sesiones.
- Una recuperación futura utilizará una credencial independiente y de un solo uso.
- Completar la recuperación revocará todas las sesiones.
- DEC-05 no implica implementar en esta etapa una UI de cambio o recuperación.
- Retención y comunicaciones de recuperación dependerán de DEC-16.

### Auditoría

Se registrarán conceptualmente los eventos `session.created`, `session.locked`, `session.unlocked`, `session.revoked`, `session.expired`, `session.logout`, `session.reauthentication_succeeded` y `session.reauthentication_failed`.

Podrán incluir `session_id`, `user_id`, audiencia, `workstation_id`, `cash_session_id`, actor, reason code, `request_id` y timestamp. Nunca incluirán secretos. Auditoría y outbox de cambios de estado serán transaccionales cuando corresponda.

### Migración desde bearer

La transición conceptual será:

1. crear persistencia de sesiones;
2. implementar login, logout, consulta de sesión y reautenticación por audiencia;
3. implementar cookies y CSRF;
4. migrar POS;
5. migrar Backoffice;
6. introducir revocación transaccional;
7. actualizar OpenAPI;
8. regenerar el cliente TypeScript desde backend;
9. retirar emisión y aceptación de bearer;
10. eliminar de los clientes las claves heredadas `zeromerma-pos-auth` y `zeromerma-backoffice-auth`;
11. no convertir automáticamente bearers heredados en sesiones;
12. responder `401` a bearers heredados después del cutover.

Si fuera imprescindible una convivencia temporal entre bearer y cookie, será acotada, bearer no se renovará, los clientes nuevos usarán sólo cookie, contará con telemetría sin secretos y se eliminará definitivamente. No se admite coexistencia permanente.

### HTTP y contratos conceptuales

- `401`: sesión ausente, inválida, revocada o expirada.
- `403`: usuario autenticado sin capability o scope exigido por DEC-03 y DEC-04.
- `423`: sesión POS bloqueada.
- `409`: conflicto de estado o unicidad cuando corresponda.
- Los errores no revelarán la existencia de usuarios por email.
- DEC-05 registra las operaciones conceptuales necesarias, pero no fija rutas OpenAPI definitivas antes de su implementación.

### Dependencias

- DEC-03: capacidades y autorización deny-by-default.
- DEC-04: scopes efectivos.
- DEC-06: carreras de cierre y restricción de caja.
- DEC-07: retries y resultados desconocidos.
- DEC-15: pérdida de red y offline.
- DEC-16: privacidad, retención, IP, user-agent y recuperación.
- DEC-17: TLS, dominios, proxy, `SameSite` y alta disponibilidad.

Estas decisiones no quedan resueltas por DEC-05.

### Hallazgos técnicos asociados

La evidencia estática registró bearer HMAC stateless con `sub` y `exp`, TTL común de 480 minutos, bearer en `localStorage` de POS y Backoffice, logout únicamente local, ausencia de idle, ausencia de una entidad Session persistente, ausencia de CSRF, CORS pendiente de endurecimiento productivo, ausencia de flujo de cambio de contraseña, `last_login_at` aparentemente actualizado mediante `flush` sin commit durable y cierre de caja sin revocación server-side.

Estos hallazgos son deuda de implementación futura y no implican cambios de código autorizados por esta decisión.

### Evidencia, tareas, consecuencias e historial

- **Evidencia:** validación técnica de `ZM-FIN-003`; implementación actual de `TokenService`, `AuthService`, `get_current_user`, stores de autenticación POS y Backoffice, `CashSession`, `Workstation`, cierre de caja, auditoría, outbox, CORS y contratos vigentes.
- **Tareas afectadas:** `ZM-FIN-003`, `ZM-FIN-008`, `ZM-FIN-015`, `ZM-FIN-016`, `ZM-FIN-017`, `ZM-FIN-018`, `ZM-FIN-019`, `ZM-FIN-020`, `ZM-FIN-021` y `ZM-FIN-022`; las tareas posteriores de cierre, idempotencia, infraestructura y seguridad deberán respetar DEC-05 conforme al Plan Maestro.
- **Consecuencias:** migración coordinada de API, POS, Backoffice, OpenAPI y cliente generado; sesiones revocables; cookies seguras; CSRF; expiración por audiencia; vínculo de sesión POS con estación y caja; pruebas de concurrencia, revocación y aislamiento.
- **Límite:** DEC-05 define la política y el modelo conceptual; no certifica que sesiones, cookies, CSRF, revocación, migraciones o contratos estén implementados o probados.
- **Historial:** `PENDIENTE` desde 2026-08-26; `APROBADA` por el propietario el 2026-08-27.

## DEC-06 — Cierre

- **Estado:** `APROBADA`
- **Fecha:** 2026-08-27
- **Propietario:** propietario de ZeroMerma
- **Contenido aprobado:** ciclo terminal de cierre, fase transaccional `CLOSING`, frontera por `CashSession`, conteo obligatorio, tratamiento de diferencias, blockers financieros, warnings no financieros, idempotencia, recuperación y correcciones compensatorias.
- **Respuesta aprobada:** política normativa, protocolos de concurrencia y cierre, errores conceptuales y estrategia de migración descritos en esta decisión.

### Ciclo de cierre

1. El ciclo normativo será `OPEN -> CLOSING -> CLOSED`.
2. `CLOSED` será terminal.
3. No existirá reapertura de un turno cerrado.
4. Una corrección posterior utilizará documentos o movimientos compensatorios auditables.
5. El cierre original no se editará, borrará ni reabrirá para corregirlo.

### Semántica técnica de `CLOSING`

`CLOSING` será una fase transaccional y no requerirá necesariamente un estado persistido mediante un commit intermedio. El modelo aprobado es:

```text
CashSession durable antes de la operación: OPEN

transacción de cierre:
  adquirir lock exclusivo de CashSession
  fase normativa CLOSING
  recalcular/validar cierre
  marcar CLOSED
  commit único
```

Consecuencias:

- no se requiere persistir durablemente `CLOSING`;
- no se requiere ampliar el enum de base de datos sólo para representar esa fase;
- no habrá commit intermedio `OPEN -> CLOSING`;
- un crash antes del commit deja durablemente `OPEN`;
- ese rollback no constituye una reapertura;
- no puede quedar un `CLOSING` durable huérfano;
- toda operación concurrente sujeta al cierre compartirá la misma frontera de locking.

`CLOSING` no se confundirá con `PENDING_CLOSE` administrativo ni con estados derivados de UI.

### Frontera de caja

El mecanismo técnico canónico derivado será:

```text
SELECT ... FOR UPDATE
sobre la CashSession concreta
```

Reglas:

1. No habrá lock global de cajas.
2. Turnos diferentes podrán progresar concurrentemente.
3. Toda operación económica que afecte un turno adquirirá la misma frontera.
4. El cierre y las operaciones consultarán la `CashSession` por identidad y después validarán su estado.
5. No será válido comprobar `OPEN`, liberar esa conclusión y confirmar efectos posteriormente sin conservar la frontera.

Resultados normativos:

```text
no_global_cash_lock=true
different_cash_sessions_can_progress_concurrently=true
close_lock_scoped_to_cash_session=true
```

### Carrera entre operación económica y cierre

#### La operación obtiene la frontera primero

```text
T1 operación adquiere CashSession OPEN
T2 cierre espera
T1 compromete su efecto
T2 adquiere la frontera
T2 recalcula el cierre incluyendo T1
```

El efecto de T1 quedará incluido en el cierre.

#### El cierre obtiene la frontera primero

```text
T1 cierre adquiere CashSession OPEN
T1 entra en fase transaccional CLOSING
T2 operación espera o recibe conflicto temporal
T1 marca CLOSED y commit
T2 adquiere o consulta después
T2 observa CLOSED
```

T2 será rechazada sin efectos. Nunca podrá existir un cierre confirmado acompañado de una venta o pago tardío del mismo turno fuera del corte.

### Operaciones sujetas a la frontera

Compartirán esta frontera todas las operaciones que puedan cambiar los importes o la composición financiera del turno, como mínimo:

```text
venta
pago operativo
devolución/reembolso
corrección con efecto financiero
anticipo de pedido
liquidación de pedido
reembolso de pedido
otros efectos financieros futuros del turno
```

La matriz exhaustiva pertenece a `ZM-FIN-008`. DEC-10, DEC-11 y DEC-14 concretarán semánticas posteriores, pero ninguna podrá dejar un efecto financiero admitido fuera del cierre de su turno.

### Conteo obligatorio

1. Todo cierre requiere conteo explícito.
2. Debe existir explícitamente el conteo `CASH`.
3. La ausencia de la fila `CASH` será inválida con código `CASH_COUNT_REQUIRED`.
4. Un conteo explícito `CASH counted_amount=0.00` será válido.
5. Una fila `CARD` o de cualquier otro medio no sustituye el conteo de efectivo.
6. No se permitirá omitir el conteo mediante una excepción ambigua de “mostrador vacío”.

### Diferencia de caja

Se conservará la convención vigente:

```text
difference_amount = counted_amount - expected_amount

> 0 = sobrante
< 0 = faltante
= 0 = cuadrado
```

Cuando la diferencia sea distinta de cero se persistirán como mínimo:

```text
expected_amount
counted_amount
difference_amount
difference_reason
actor
timestamp
audit
```

Reglas:

- la diferencia no impedirá por sí sola cerrar;
- la razón será obligatoria cuando `difference != 0`;
- no se alterará `expected_amount` para forzar cuadratura;
- no se creará automáticamente un movimiento ficticio para compensarla;
- no se ocultará la diferencia;
- quedará como información financiera auditable del cierre.

DEC-06 no fija un umbral monetario arbitrario. Un futuro umbral de alto impacto podrá activar capability o aprobación adicional conforme a DEC-03, sin cambiar la regla de que el cierre final registre explícitamente la diferencia.

### Blockers financieros

Bloqueará el cierre toda operación financiera admitida pero no terminal que todavía pueda alterar el turno. Esto incluye conceptualmente:

```text
pago pendiente
anticipo pendiente
liquidación pendiente
reembolso pendiente
operación externa PROCESSING
operación externa UNKNOWN
otro efecto financiero admitido no resuelto
```

Reglas:

```text
UNKNOWN != FAILED
UNKNOWN != safe_to_close
```

El efecto deberá resolverse o reconciliarse antes del cierre. DEC-07 gobierna idempotencia y recuperación; DEC-14 concretará pagos externos.

### Warnings no financieros

Un documento pendiente que no pueda modificar el efectivo o los medios de pago del turno podrá generar un warning sin bloquear. Una transferencia física en tránsito es un ejemplo cuando no afecta el ledger financiero del turno.

Los warnings operativamente relevantes quedarán visibles y auditables. No se convertirá automáticamente toda deuda física en blocker de caja.

### Pedidos

1. La mera existencia de un pedido abierto no bloqueará el cierre.
2. Sí bloqueará un efecto financiero de pedido perteneciente al turno que haya sido admitido y permanezca pendiente o no resuelto.
3. Todo anticipo, liquidación o reembolso asociado al turno quedará representado en el ledger financiero canónico consumido por cash close.
4. Ningún pago de pedido podrá quedar fuera del expected o de la reconciliación del turno que lo recibió.

La regla de interfaz será:

```text
todo efecto financiero de pedido
admitido y asociado a un turno
debe quedar atómicamente representado
en el ledger canónico consumido por cash close
```

DEC-10 decidirá cuándo nace exactamente cada efecto económico del pedido.

### `CLASS_CAPTURE` y reconciliación física

- Una reconciliación física pendiente que pueda completarse correctamente como parte del cierre no será por sí sola motivo para mantener el turno abierto indefinidamente.
- Si al momento del commit permanece una inconsistencia física obligatoria no resuelta, será blocker.
- DEC-08 definirá el ledger y el inventario físico definitivos.

DEC-06 no resuelve la semántica completa de inventario.

### Idempotencia del cierre

Conforme a DEC-07:

```text
operation_code=cash_session.close
Idempotency-Key obligatoria
```

#### Misma key

```text
misma key + mismo fingerprint + COMPLETED
=> replay del mismo cierre
=> cero efectos nuevos
```

Dos requests simultáneas con la misma key producirán un único efecto.

#### Dos keys diferentes para la misma `CashSession`

Serán dos intenciones distintas, pero sólo una podrá comprometer el cierre. La segunda quedará terminalmente:

```text
REJECTED
error_code=CASH_CLOSE_ALREADY_EXISTS
HTTP=409
```

La segunda intención no creará un segundo cierre, una segunda auditoría del efecto, un segundo outbox del efecto ni una segunda revocación.

### Recuperación

Si un cierre es interrumpido se cumplirán:

```text
no_auto_reopen=true
no_second_close=true
same_key_recovery=true
```

- crash antes del lock: retry normal;
- crash con lock y antes del commit: rollback; durablemente continúa `OPEN`;
- crash después de los cálculos pero antes del commit: rollback conjunto;
- commit exitoso con respuesta perdida: replay `COMPLETED` con la misma key.

No existirá `timeout -> CLOSING -> OPEN`, porque no habrá un `CLOSING` durable comprometido. Tampoco se creará un nuevo cierre como mecanismo de recuperación.

### Relación con DEC-05

Dentro de la misma transacción que comprometa `CashSession -> CLOSED` se revocarán:

```text
todas las AuthSession POS ACTIVE o LOCKED
ligadas mediante cash_session_id
al turno cerrado
```

La razón será `CASH_SESSION_CLOSED`. Esto no significa revocar todas las sesiones del usuario, todas las sesiones de la estación ni únicamente el navegador que ejecutó el cierre.

Una sesión `LOCKED` por idle no cerrará la caja. Una sesión expirada no podrá ejecutar una mutación de cierre.

### Correcciones posteriores

`CLOSED` será inmutable. Una corrección posterior deberá:

- referenciar el cierre o documento original;
- utilizar un documento o movimiento compensatorio;
- mantener relación causal;
- registrar actor, razón y fecha;
- producir auditoría y outbox;
- no cambiar `expected`, `counted` ni `difference` originales;
- no reabrir el cierre.

La forma exacta del documento compensatorio queda para implementación posterior.

### Contratos y errores conceptuales

Los códigos estables serán:

```text
CASH_SESSION_CLOSING
CASH_SESSION_CLOSED
CASH_COUNT_REQUIRED
CASH_PENDING_FINANCIAL_OPERATION
CASH_CLOSE_ALREADY_EXISTS
CASH_CLOSE_DIFFERENCE_REASON_REQUIRED
```

Semántica HTTP recomendada:

```text
409:
  conflictos de estado, frontera, cierre existente o pendiente financiero

422:
  conteo requerido
  razón de diferencia requerida
```

`CASH_SESSION_CLOSING` sólo aplicará cuando la implementación utilice espera acotada, `NOWAIT` o equivalente y pueda detectar temporalmente la frontera ocupada. Los errores serán estructurados para consumo del frontend.

### Auditoría y outbox

Los eventos conceptuales serán:

```text
cash_close.committed
cash_close.rejected
cash_close.difference_recorded
```

`cash_close.started` no será obligatorio como evento durable cuando `CLOSING` sea sólo transaccional.

Un cierre confirmado auditará como mínimo:

```text
actor
cash_session_id
close_id
expected
counted
difference
difference_reason
warnings o blockers relevantes
request_id
referencia idempotente no secreta
timestamp
```

Un replay no generará un segundo evento de negocio. `cash_close.difference_recorded` aparecerá exactamente una vez cuando corresponda. Cierre, auditoría, outbox, revocaciones de DEC-05 e idempotencia de DEC-07 compartirán la unidad transaccional cuando corresponda.

### Rendimiento y UX

```text
different_cash_sessions_concurrent=true
close_lock_scoped_to_cash_session=true
preview_does_not_establish_close_boundary=true
final_commit_revalidates=true
```

- El usuario podrá obtener un preview antes del lock final.
- El preview no reservará el derecho a cerrar.
- La interacción de conteo del usuario no mantendrá bloqueada la fila.
- La transacción final recalculará expected, blockers y datos críticos tras adquirir la frontera.
- No se realizarán llamadas externas bajo el lock.
- Worker y outbox consumer no formarán parte del commit síncrono.
- Cajas distintas progresarán en paralelo.

DEC-06 no fija un SLA numérico sin una línea base.

### Migración conceptual

1. Mantener durablemente `CashSession.status` con `OPEN/CLOSED` inicialmente.
2. Modelar `CLOSING` como fase transaccional.
3. Introducir un helper o unidad de trabajo canónica de `CashSession FOR UPDATE`.
4. Migrar las operaciones financieras del turno a esa frontera.
5. Recalcular el cierre final bajo lock.
6. Exigir conteo `CASH` explícito.
7. Añadir una razón inequívoca de diferencia.
8. Añadir detección canónica de pendientes financieros.
9. Integrar DEC-07.
10. Integrar la revocación de DEC-05.
11. Conservar `UNIQUE(cash_session_id)` del cierre.
12. Añadir errores de dominio estables.
13. Actualizar OpenAPI desde backend.
14. Regenerar el cliente TypeScript.
15. Actualizar POS.
16. Preservar cierres históricos sin inventar razones ni reinterpretar datos existentes.

Esta decisión no implementa ninguno de estos cambios.

### Pruebas futuras obligatorias

#### Concurrencia

- venta obtiene el lock primero;
- cierre obtiene el lock primero;
- pago contra cierre en ambos órdenes;
- efectos financieros de pedido contra cierre;
- misma key de cierre simultánea;
- dos keys distintas;
- cierres de cajas diferentes en paralelo.

#### Conteo

- `CASH` ausente;
- `CASH=0`;
- conteo exacto;
- diferencia positiva;
- diferencia negativa;
- diferencia sin razón;
- `CARD` sin `CASH`;
- filas inválidas o duplicadas.

#### Blockers y warnings

- pendiente financiero;
- `PROCESSING`;
- `UNKNOWN`;
- pedido abierto sin pendiente financiero;
- transferencia en tránsito;
- reconciliación física resuelta y no resuelta.

#### Recuperación

- crash antes del lock;
- crash con lock;
- crash antes del commit;
- respuesta perdida;
- replay.

#### Integración

- revocación exacta de `AuthSession`;
- audit exactly once;
- outbox exactly once;
- idempotency exactly once;
- `CLOSED` no reabrible;
- corrección posterior sin modificación del cierre original.

### Dependencias

- DEC-05: revocación de sesiones POS.
- DEC-07: retry, replay e idempotencia.
- DEC-08: reconciliación física e inventario.
- DEC-10: timing económico de pedidos.
- DEC-11: clasificación y reconciliación de medios.
- DEC-14: estados externos `PROCESSING` y `UNKNOWN`.
- DEC-19: históricos y datos existentes.

Estas decisiones no quedan resueltas por DEC-06.

### Evidencia técnica asociada

La validación estática de `ZM-FIN-003` comprobó:

- `CashSession` actual sólo admite `OPEN/CLOSED`;
- ausencia de row lock transversal;
- venta, pagos y devoluciones sin una frontera común;
- cierre actual con expected calculado antes del lock;
- conteo `CASH` actualmente no exigido inequívocamente;
- diferencia actual calculada como `counted - expected`;
- `CustomerOrderPayment` vinculado a `cash_session_id` pero fuera del ledger consumido por cierre;
- `UNIQUE(cash_session_id)` existente para el cierre;
- auditoría y outbox actuales añadidos a la misma sesión SQLAlchemy;
- ausencia de pruebas concurrentes entre operación y cierre.

Estos hechos describen el código vigente y no equivalen a implementación de DEC-06.

### Consecuencias, límite e historial

- **Consecuencias:** frontera transaccional común para cierre y operaciones económicas, integración con DEC-05 y DEC-07, ledger financiero completo, contratos estables y pruebas concurrentes.
- **Límite:** DEC-06 define la política y el modelo técnico; no certifica que locking, conteo, blockers, idempotencia, revocación, contratos o pruebas estén implementados.
- **Historial:** `PENDIENTE` desde 2026-08-26; `APROBADA` por el propietario el 2026-08-27.

## DEC-07 — Idempotencia

- **Estado:** `APROBADA`
- **Fecha:** 2026-08-27
- **Propietario:** propietario de ZeroMerma
- **Contenido aprobado:** mecanismo transversal de idempotencia para comandos críticos, clave UUIDv7 globalmente única, fingerprint contextual versionado, replay sin repetición de efectos, atomicidad con negocio, auditoría y outbox, recuperación de errores y estado externo incierto, retención y condiciones de concurrencia y rendimiento.
- **Respuesta aprobada:** política normativa, modelo conceptual, cobertura inicial y estrategia de migración descritos en esta decisión.

### Política normativa aprobada

1. ZeroMerma utilizará un mecanismo transversal y uniforme de idempotencia para comandos críticos.
2. Ningún módulo definirá una semántica de idempotencia incompatible con este mecanismo canónico.
3. La infraestructura será automática y no añadirá aprobaciones humanas ni pasos operativos adicionales.
4. Cada nueva intención utilizará una `Idempotency-Key` UUIDv7.
5. Todos los retries de la misma intención reutilizarán exactamente la misma key.
6. Una intención nueva utilizará una key nueva.
7. La key no sustituirá el ID de dominio del documento.
8. La identidad idempotente tendrá unicidad global mediante `UNIQUE(idempotency_key)`.
9. La misma key nunca podrá utilizarse para otra operación, actor o contexto.
10. Una reutilización incompatible devolverá `409 IDEMPOTENCY_KEY_REUSED` sin efectos nuevos.

### Replay

La equivalencia de replay será:

```text
misma key
+ misma operación
+ mismo actor/contexto
+ mismo payload canónico
= mismo resultado lógico
+ cero repetición de efectos
```

Una reutilización incompatible será:

```text
misma key
+ operación/contexto/payload diferente
= 409
+ cero efectos nuevos
```

Un retry ya completado no volverá a ejecutar el servicio de dominio.

### Fingerprint canónico

El fingerprint será versionado e incluirá conceptualmente:

```text
fingerprint_version
operation_code
actor_user_id
branch_id cuando aplique
workstation_id cuando aplique
cash_session_id cuando aplique
payload canónico
```

La canonización deberá:

- ordenar las claves JSON de manera estable;
- normalizar UUID;
- normalizar enums;
- normalizar fechas UTC;
- normalizar `Decimal` conforme a la escala contractual;
- conservar el orden de arrays, salvo cuando el contrato declare una colección como conjunto;
- aplicar defaults contractuales antes del hash;
- distinguir `null` y ausencia, salvo equivalencia contractual explícita;
- usar un hash criptográfico equivalente a SHA-256.

No incluirá cookies, contraseñas, secretos, `X-Request-ID` ni la propia `Idempotency-Key`.

### Modelo conceptual canónico

La entidad transversal será equivalente a:

```text
IdempotencyRecord
  id
  idempotency_key
  operation_code
  fingerprint_version
  request_fingerprint
  actor_user_id
  branch_id nullable
  workstation_id nullable
  cash_session_id nullable
  status
  resource_type nullable
  resource_id nullable
  response_status nullable
  response_schema_version nullable
  response_reference nullable
  response_payload nullable
  error_code nullable
  first_request_id nullable
  created_at
  updated_at
  completed_at nullable
  response_expires_at nullable
```

Los estados canónicos serán:

```text
PROCESSING
COMPLETED
REJECTED
UNKNOWN
```

- `PROCESSING`: comando admitido o en curso.
- `COMPLETED`: resultado comprometido.
- `REJECTED`: rechazo determinista admitido y terminal.
- `UNKNOWN`: resultado externo incierto; no equivale a fallo.

Los workflows externos podrán incorporar campos técnicos de lease y reconciliación derivados de una implementación posterior. No se registrará un `expires_at` que elimine la identidad idempotente y vuelva a permitir duplicación histórica.

### Atomicidad

Para comandos internos deberán quedar en una única unidad transaccional:

```text
IdempotencyRecord
documento de negocio
movimientos económicos
movimientos físicos
auditoría
outbox
resultado idempotente
```

`COMPLETED` nunca se confirmará en una transacción posterior e independiente al documento de negocio. Un crash antes del commit revertirá conjuntamente todos esos efectos. Las constraints de dominio actuales se conservarán como defensa adicional.

### Errores

#### Antes de admisión

Los errores de schema o key inválida, `401`, `403` y demás validaciones previas no consumen la key.

#### Después de admisión

Un rechazo de negocio determinista podrá persistirse como `REJECTED`; un replay devolverá el mismo resultado lógico.

#### Error transitorio antes de commit

Un `500` inesperado, deadlock, serialization failure o timeout antes de commit provocará rollback completo y permitirá retry con la misma key.

#### Commit exitoso y respuesta perdida

El retry recuperará `COMPLETED` sin repetir efectos. Un comando compensatorio será una nueva intención y utilizará otra key.

### Concurrencia

- Dos requests con la misma key competirán únicamente por esa identidad.
- Una request ejecutará los efectos; la otra esperará de forma acotada o recibirá un estado o conflicto temporal y después hará replay.
- No habrá lock por `operation_code`.
- Keys diferentes podrán procesarse concurrentemente.
- Sucursales distintas no se serializarán por el mecanismo idempotente.
- Operaciones no relacionadas tampoco se serializarán.
- No se fija en esta decisión un timeout numérico de espera.

Las condiciones normativas de rendimiento serán:

```text
no_global_serialization=true
unrelated_commands_can_run_concurrently=true
idempotency_lookup_indexed=true
lock_scope_minimized=true
external_dependency_in_sync_path=false
human_approval_added=false
```

### Condición explícita de rendimiento

DEC-07 fue aprobada por el propietario bajo la condición de que:

> La idempotencia no debe entorpecer la operación, hacer lento materialmente el sistema ni ralentizar la toma de decisiones del operador.

Como consecuencia:

1. no habrá cola global;
2. no habrá serialización global;
3. no habrá aprobación humana;
4. el lookup será indexado;
5. el bloqueo se limitará al mínimo ámbito necesario;
6. worker, outbox consumer, batch o servicio externo no serán requisito del fast-path síncrono para comandos internos;
7. el procesamiento de outbox seguirá siendo asíncrono;
8. los replays `COMPLETED` usarán fast-path;
9. la implementación futura requerirá pruebas de concurrencia y regresión de rendimiento.

Los SLA y umbrales numéricos de latencia dependerán de una línea base y métricas posteriores; no se inventan en DEC-07.

### Fast path

Para un record `COMPLETED` se deberá:

1. autenticar la request actual;
2. buscar por el índice único de `idempotency_key`;
3. verificar operación, contexto y fingerprint;
4. revalidar la autorización vigente conforme a DEC-03 y DEC-04;
5. devolver el snapshot o la referencia persistida.

No se volverán a ejecutar el servicio de dominio, pricing, cálculos físicos, adapters externos, worker ni outbox consumer. Conocer una key nunca concede acceso al recurso.

### `X-Request-ID`

```text
X-Request-ID = identidad/correlación de una request HTTP
Idempotency-Key = identidad durable de una intención de negocio
```

Un retry podrá utilizar un nuevo `X-Request-ID` con la misma `Idempotency-Key`. `X-Request-ID` no será sustituto de idempotencia. El campo actual de pedidos denominado `idempotency_key`, que sólo se usa como `request_id`, deberá migrarse posteriormente a la semántica canónica.

### Estado externo incierto

```text
UNKNOWN != FAILED
UNKNOWN != SAFE_TO_RETRY
```

Si una integración externa futura produce un resultado incierto, no se repetirá ciegamente el efecto; se conservará la identidad idempotente, se devolverá un estado o referencia de seguimiento, se reconciliará usando la misma identidad y se permitirá la transición posterior a un estado terminal. El proveedor, la autorización, la captura, la reversa y las reglas específicas pertenecen a DEC-14.

### Crash recovery

#### Comandos internos

Un `PROCESSING` interno no quedará comprometido durablemente separado de sus efectos:

- crash antes del commit: rollback y retry;
- commit exitoso: `COMPLETED` recuperable.

#### Operaciones externas o asíncronas

Un `PROCESSING` o `UNKNOWN` durable podrá ser tomado por reconciliación mediante un lease técnico. La expiración de un lease no autoriza repetir ciegamente el efecto externo; sólo autoriza continuar la reconciliación.

### Retención

#### Identidad idempotente

Se conservará información suficiente para impedir duplicaciones y verificar key, operación, contexto, fingerprint, status y referencia al recurso o resultado.

#### Payload de respuesta

Podrá purgarse antes cuando exista un snapshot compacto o una referencia estable suficiente.

#### Payload original

No será necesario conservarlo cuando el fingerprint y los metadatos canónicos sean suficientes.

#### Auditoría

Tendrá su propia política y no sustituirá al record idempotente.

#### Retención legal

Dependerá de DEC-16; DEC-07 no fija una duración legal definitiva.

### Cobertura inicial obligatoria

Como mínimo, requerirán idempotencia las mutaciones críticas equivalentes a:

```text
cash_session.open
cash_session.close
sale.confirm
operational_payment.create

order.create
order.mark_ready
order.deliver
order.cancel
pagos/reembolsos independientes de pedido si aparecen

return.commit
correction.commit
waste.commit
inventory.adjust

counter_transfer.commit
transfer.create
transfer.update
transfer.dispatch
transfer.receive
transfer.cancel

purchase.create
purchase.update
purchase.confirm
purchase.receive
purchase.cancel
direct purchase entry

production.create
production.update
production.start
production.complete
production.cancel

role.permissions.replace
user_role.assign
user_role.remove
scope/branch assignment
superadmin privilege changes
break-glass execution
```

Las lecturas, búsquedas y previews sin efectos no requerirán `Idempotency-Key`. Una acción física como reimpresión podrá requerir una regla específica posterior conforme a DEC-15. La matriz exhaustiva definitiva pertenece a `ZM-FIN-008`.

### Relación con DEC-05

- `AuthSession` e `Idempotency-Key` son identidades distintas.
- Expirar o revocar una sesión no altera una intención ya comprometida.
- Tras un login nuevo, el mismo usuario podrá recuperar una intención propia si conserva autorización vigente.
- Un actor diferente no podrá utilizar la key como credential.
- Un usuario que perdió capability o scope no obtendrá el resultado mediante replay.
- No será necesario que una cash session histórica continúe abierta para consultar un resultado ya comprometido y autorizado.
- Una intención nueva resolverá nuevamente el contexto vigente.

### Relación con DEC-06

DEC-07 permitirá el retry del cierre, recuperar el mismo cierre tras una respuesta perdida, impedir doble efecto para la misma key y devolver el cierre existente mediante fast-path.

DEC-07 no decide si gana una venta o el cierre, qué locks usa el cierre, qué ocurre con dos keys distintas de cierre ni cuándo rechazar operaciones tardías. Esas reglas pertenecen a DEC-06.

### Migración conceptual

1. Crear la infraestructura transversal `IdempotencyRecord`.
2. Añadir `Idempotency-Key` requerida a los comandos `REQUIRED`.
3. Validar UUIDv7 en backend.
4. Conservar `X-Request-ID` separado.
5. Generar UUIDv7 por intención en POS y Backoffice.
6. Conservar la key en el estado cliente hasta obtener un resultado terminal.
7. Introducir una unidad de trabajo idempotente transversal.
8. Retirar commits internos incompatibles dentro de servicios críticos.
9. Compartir la transacción con documento, ledgers, auditoría y outbox.
10. Corregir `AdminOrderActionRequest.idempotency_key`.
11. Actualizar OpenAPI desde backend.
12. Regenerar el cliente TypeScript.
13. Retirar helpers que aparenten idempotencia mediante request IDs o UUIDv4.
14. Conservar constraints de negocio útiles.
15. Añadir telemetría de hit, miss, replay, mismatch y contention sin payload sensible.
16. No convertir históricos `X-Request-ID` en records idempotentes sin evidencia.

Esta estrategia es conceptual; no implementa cambios en esta iteración.

### Pruebas futuras obligatorias

La implementación deberá cubrir como mínimo:

- misma key con mismo payload;
- misma key con payload diferente;
- misma key con operación diferente;
- misma key con contexto diferente;
- concurrencia de N requests con la misma key;
- concurrencia con keys diferentes;
- sucursales independientes;
- respuesta perdida;
- crash antes y después de commit;
- rechazo determinista;
- retry tras deadlock o serialization failure;
- auditoría exactamente una vez;
- outbox exactamente una vez;
- `UNKNOWN` externo sin duplicación;
- autorización actual durante replay;
- fast-path sin dominio, adapters ni workers;
- replay tras purga del payload;
- ausencia de serialización global;
- benchmark y regresión de overhead.

No se fijará un umbral numérico sin una línea base.

### Dependencias

- DEC-05: autenticación y autorización del replay.
- DEC-06: cierre y carreras.
- DEC-08–DEC-13: comandos económicos y físicos.
- DEC-14: operaciones externas y `UNKNOWN`.
- DEC-15: offline y hardware.
- DEC-16: retención.
- DEC-17: alta disponibilidad, recovery y leases.
- DEC-19: datos existentes.

Estas decisiones no se resuelven mediante DEC-07.

### Evidencia, tareas, consecuencias e historial

- **Evidencia:** validación técnica de `ZM-FIN-003`; ausencia actual de `Idempotency-Key` canónica y de modelo o tabla transversal; `X-Request-ID` usado sólo para trazabilidad; pseudo-`idempotency_key` de pedidos usado como `request_id`; guards frontend contra doble submit; constraints particulares de negocio; auditoría y outbox capaces de compartir sesión; commits actuales distribuidos entre servicios.
- **Distinciones obligatorias:** trazabilidad no equivale a idempotencia; un guard de doble submit en UI no equivale a idempotencia; una constraint única de negocio no equivale a idempotencia transversal.
- **Tareas afectadas:** `ZM-FIN-003`, `ZM-FIN-008` y las tareas posteriores del Plan Maestro que implementen idempotencia, operaciones económicas y físicas, cierre, pagos externos, offline, retención, continuidad y migración de datos.
- **Consecuencias:** nueva persistencia transversal, unidad de trabajo compartida, cambios de contrato backend-first, regeneración del cliente TypeScript, adopción coordinada por POS y Backoffice y pruebas de atomicidad, concurrencia, recuperación y rendimiento.
- **Límite:** DEC-07 define la política y el modelo conceptual; no certifica que la idempotencia, las migraciones, los contratos, los clientes o las pruebas estén implementados.
- **Historial:** `PENDIENTE` desde 2026-08-26; `APROBADA` por el propietario el 2026-08-27.

## DEC-08 — Inventario

- **Estado:** `APROBADA`
- **Fecha:** 2026-08-27
- **Propietario:** propietario de ZeroMerma
- **Contenido aprobado:** ledger causal e inmutable, balance materializado con existencia y reservas, afectación física de `PRODUCT_DIRECT`, obligaciones y atribuciones de `CLASS_CAPTURE`, reservas, transferencias, producción, compras, UOM, stock negativo, reversas, locking, rendimiento y migración conceptual.
- **Respuesta aprobada:** política normativa, modelos conceptuales, invariantes, dependencias y pruebas futuras descritos en esta decisión.

### Ledger causal

1. Todo cambio de existencias tendrá un movimiento causal de inventario.
2. Ningún saldo podrá modificarse silenciosamente sin un movimiento que explique el efecto.
3. Cada movimiento identificará como mínimo:
   - producto;
   - sucursal;
   - ubicación;
   - cantidad;
   - UOM;
   - documento origen;
   - línea origen cuando aplique;
   - tipo o efecto causal;
   - actor y contexto;
   - timestamp.
4. Los movimientos serán inmutables.
5. Las correcciones y reversas físicas utilizarán nuevos movimientos compensatorios.
6. No se borrarán ni editarán movimientos históricos para cuadrar saldos.

### Modelo canónico de balances

El balance materializado persistirá:

```text
quantity_on_hand
quantity_reserved

available =
quantity_on_hand - quantity_reserved
```

La semántica será:

```text
on_hand:
existencia física

reserved:
existencia comprometida pero todavía no consumida

available:
existencia realmente disponible para nuevas operaciones
```

Reglas:

- se persistirán `on_hand` y `reserved`;
- `available` se derivará;
- no se persistirá una tercera fuente redundante que pueda generar drift;
- la lectura operacional se realizará desde el balance materializado;
- el ledger inmutable será la fuente de causalidad y reconciliación;
- no se escaneará todo el ledger en cada venta.

Resultados normativos:

```text
operational_reads_use_balance=true
ledger_remains_source_of_causality=true
no_full_ledger_scan_per_sale=true
```

### Modelo conceptual de movimiento

La entidad será equivalente a:

```text
InventoryMovement
  id
  branch_id
  product_id
  location_code
  movement_type
  quantity_base
  base_uom
  source_quantity
  source_uom
  conversion_factor
  source_document_type
  source_document_id
  source_line_id nullable
  causal_operation_code
  causal_effect_code
  idempotency_record_id
  reversal_of_movement_id nullable
  actor_user_id
  occurred_at
```

La forma física exacta podrá adaptarse durante la implementación, pero deberá preservar estas invariantes. La protección contra efectos duplicados tendrá una constraint causal equivalente a:

```text
UNIQUE(idempotency_record_id, causal_effect_code)
```

Se admitirá una estructura técnicamente equivalente si garantiza exactamente un delta por efecto causal. La clave causal y la `Idempotency-Key` de DEC-07 serán defensas complementarias.

### `PRODUCT_DIRECT`

1. Una venta `PRODUCT_DIRECT` descontará físicamente inventario al confirmar la venta.
2. Para la operación POS vigente, la ubicación canónica será `COUNTER`, salvo que una operación futura declare explícitamente otra ubicación.
3. Antes de confirmar el movimiento se validará disponibilidad bajo locking.
4. El movimiento quedará vinculado a la línea de venta.
5. El decremento ocurrirá exactamente una vez.
6. Venta, balance, movimiento, auditoría, outbox e idempotencia compartirán la misma unidad transaccional.
7. Un replay `COMPLETED` no volverá a descontar inventario.

### `CLASS_CAPTURE`

Al confirmar una venta `CLASS_CAPTURE`:

- no se inventará un SKU concreto;
- no se descontará genéricamente una pieza física;
- se creará una obligación física pendiente por línea de venta, clase y cantidad.

El modelo conceptual será equivalente a:

```text
ClassInventoryObligation
  id
  sale_id
  sale_line_id UNIQUE
  branch_id
  product_class_id
  quantity_required
  quantity_attributed
  status
```

y las atribuciones serán equivalentes a:

```text
ClassInventoryAttribution
  obligation_id
  product_id
  quantity
  efecto causal/idempotente
```

Invariantes:

```text
quantity_required > 0
0 <= quantity_attributed <= quantity_required

pending =
quantity_required - quantity_attributed

FULFILLED iff pending = 0
```

Reglas:

1. Cada producto atribuido deberá pertenecer a la clase correspondiente.
2. No podrá atribuirse más cantidad que la pendiente.
3. Cada atribución generará el movimiento físico exacto del SKU concreto.
4. Cada atribución y su movimiento físico se confirmarán exactamente una vez.
5. No podrá existir:
   - doble descuento;
   - sobre-atribución;
   - obligación completada sin movimientos correspondientes;
   - movimiento sin atribución causal.
6. La suma de atribuciones deberá coincidir con la obligación para considerarla cumplida.
7. Obligación, atribución, balance, movimiento, auditoría, outbox e idempotencia deberán ser consistentes.
8. Conforme a DEC-06, una inconsistencia física obligatoria no resuelta al commit del cierre será blocker.

Ejemplo normativo:

```text
Venta:
5 unidades de clase Conchas

Obligación:
Conchas pending=5

Reconciliación:
3 Concha vainilla
2 Concha chocolate

Movimientos:
Concha vainilla COUNTER -3
Concha chocolate COUNTER -2

Resultado:
pending=0
```

No existirá ningún descuento adicional de cinco unidades genéricas.

### Reservas

Existirá un modelo causal de reserva separado del saldo materializado, conceptualmente equivalente a:

```text
InventoryReservation
  id
  branch_id
  product_id
  location_code
  source_document_type
  source_document_id
  source_line_id
  quantity_base
  consumed_quantity
  released_quantity
  status
  idempotency_record_id
```

Los estados serán equivalentes a:

```text
ACTIVE
PARTIALLY_CONSUMED
CONSUMED
RELEASED
```

Efectos:

```text
RESERVE:
  on_hand no cambia
  reserved aumenta
  available disminuye

RELEASE:
  on_hand no cambia
  reserved disminuye
  available aumenta

CONSUME:
  on_hand disminuye
  reserved disminuye
```

Invariantes:

```text
reserved >= 0
consumed + released <= reserved_original
```

Una reserva no podrá liberarse ni consumirse dos veces. El balance materializará `quantity_reserved`; la entidad de reserva preservará la causalidad.

### Pedidos

La política de inventario aprobada será:

```text
READY -> reserva producto exacto
CANCELED/EXPIRED -> libera reserva
DELIVERED -> consume reserva
```

Reglas:

- `READY` requerirá disponibilidad suficiente para la reserva aprobada;
- no se reservará y descontará `on_hand` simultáneamente por la misma cantidad;
- la entrega consumirá exactamente la reserva correspondiente;
- la cancelación o expiración liberará exactamente la reserva restante;
- delivery y cancelación concurrentes se serializarán para que sólo una transición terminal comprometa efectos.

Los siguientes detalles pertenecen a DEC-10 y no se resuelven en DEC-08:

- reserva parcial o backorder;
- expiración comercial;
- pedidos `CLASS_CAPTURE`;
- sustituciones;
- cambios de producto después de reservar.

### Transferencias

#### Dispatch

```text
source on_hand -= quantity
IN_TRANSIT += quantity
```

#### Receive

```text
IN_TRANSIT -= received_quantity
destination on_hand += received_quantity
```

Reglas:

1. La diferencia entre enviado y recibido no desaparecerá.
2. Una recepción parcial dejará explícitamente el remanente en tránsito hasta su resolución.
3. Pérdida, daño o merma en tránsito requerirá un movimiento causal posterior.
4. Cancelar antes del dispatch no generará efecto físico.
5. Cancelar después del dispatch no podrá limitarse a cambiar un status; requerirá retorno o disposición causal.
6. La recepción será idempotente.
7. El scope de origen y destino obedecerá DEC-04.
8. Todos los balances relacionados se bloquearán en orden canónico.
9. POS y Backoffice deberán converger posteriormente en una única semántica física.

La implementación vigente de transferencia administrativa puede eliminar una diferencia de tránsito sin un movimiento causal explícito; este comportamiento deberá corregirse durante la implementación de DEC-08.

### Producción

DEC-08 fija los requisitos físicos generales:

```text
DRAFT -> sin efecto físico

START ->
reserva de insumos
o movimiento a WIP
según DEC-12

COMPLETE ->
consumo real
+ retornos/sobrantes
+ merma
+ output real

CANCEL antes de uso ->
liberar

CANCEL después de uso ->
disposición causal explícita
```

Reglas:

- iniciar producción impedirá que los mismos insumos queden simultáneamente disponibles para otras operaciones;
- completar producción registrará todos los efectos físicos relevantes;
- cancelar después del uso físico no restaurará automáticamente los insumos como si nunca se hubieran utilizado.

DEC-12 resolverá la elección definitiva entre reserva y WIP, el momento de consumo irreversible, el output parcial, el rendimiento y el consumo real frente al planificado.

### Compras

```text
create -> no stock
confirm -> no stock
receive -> on_hand aumenta
```

Una entrada directa sólo aumentará inventario cuando represente una recepción física confirmada. Cada recepción incluirá:

- documento y línea de recepción;
- UOM y factor utilizados;
- cantidad base;
- movimiento causal;
- incremento de balance;
- auditoría;
- outbox;
- idempotencia.

Crear o aprobar una compra no aumentará existencias físicas por sí solo.

### Devoluciones

DEC-08 define que el ledger será capaz de representar los efectos físicos que DEC-09 apruebe posteriormente. Como mínimo podrá expresar:

```text
RESTOCK_COUNTER
-> movimiento IN COUNTER

RESTOCK_BACKROOM
-> movimiento IN BACKROOM

SEND_TO_WASTE
-> movimiento causal hacia WASTE/no vendible

QUARANTINE futuro
-> ubicación no vendible

NO_STOCK
-> sin movimiento sólo cuando el elemento no sea inventariable
```

DEC-09 decidirá cuándo podrá utilizarse cada disposición; DEC-08 no las aprueba como política final de devolución.

### Merma

La semántica física futura será única:

```text
documento de merma confirmado
=> efecto físico causal exactamente una vez
=> salida de ubicación vendible
=> entrada a WASTE o disposición terminal según DEC-09
```

POS y Backoffice no conservarán comportamientos físicos diferentes para la misma operación.

El código vigente presenta esta divergencia:

```text
POS waste:
  documento sí
  movimiento no

Admin waste:
  documento sí
  movimiento/balance sí
```

Esta divergencia deberá eliminarse posteriormente.

### UOM y conversiones

1. Cada producto tendrá una UOM base canónica.
2. Los movimientos físicos se expresarán finalmente en esa UOM base.
3. Cuando la operación use otra UOM se conservará este snapshot:

```text
source_quantity
source_uom
conversion_factor
base_quantity
base_uom
```

4. `conversion_factor` será positivo cuando exista conversión.
5. El cálculo utilizará `Decimal/Numeric`, nunca float.
6. Cambiar después el factor del producto o proveedor no alterará movimientos históricos.
7. Una conversión inversa para presentación no reescribirá el ledger.
8. La precisión y cuantización seguirán la convención contractual vigente y se documentarán durante la implementación.
9. Los datos y UOM históricos ambiguos dependerán de DEC-19.

### Stock negativo

#### Operaciones ordinarias

Las operaciones ordinarias no podrán producir stock negativo. Antes de comprometer una operación se deberá:

```text
lock saldo/reserva
require available >= required
```

La falta de disponibilidad producirá un rechazo sin efectos.

#### Ajuste excepcional

Un ajuste o conciliación excepcional podrá producir saldo negativo únicamente con:

```text
inventory.adjust
intención explícita de permitir negativo
reason obligatorio
audit
outbox
idempotency
```

No se requiere una capacidad adicional a `inventory.adjust` para establecer DEC-08. El saldo negativo nunca será silencioso, nunca será consecuencia normal de venta, pedido, transferencia o producción y permanecerá visible y auditable.

### Correcciones y reversas

```text
movimiento original:
  inmutable

movimiento de reversa:
  nuevo movimiento
  efecto opuesto
  referencia al original
```

Reglas:

- no se borrará el original;
- no se editará su cantidad histórica;
- será obligatoria una relación `reversal_of_movement_id` o equivalente;
- existirá un documento causal nuevo;
- se registrarán razón y actor;
- la reversa tendrá idempotencia propia;
- se impedirá la doble reversa del mismo efecto bajo el mismo documento causal;
- la cadena causal deberá ser reconstruible.

Corregir datos maestros no constituirá automáticamente un movimiento físico.

### Locking y concurrencia

Los principios técnicos serán:

```text
no_global_inventory_lock=true
different_products_can_progress_concurrently=true
different_branches_can_progress_concurrently=true
causal_duplicates_prevented=true
```

El orden canónico conceptual será:

```text
1. IdempotencyRecord
2. documento/estado de negocio
3. CashSession cuando DEC-06 aplique
4. InventoryBalance ordenados determinísticamente
5. Reservation/Obligation correspondientes
6. efectos
7. commit
```

Los balances se ordenarán mediante una clave determinista equivalente a:

```text
branch_id
product_id
location_code
```

Las transferencias bloquearán origen, tránsito y destino siguiendo el mismo orden canónico, no "origen primero". Producción ordenará conjuntamente insumos y outputs. No existirá un lock global de inventario.

### Causalidad y DEC-07

En las mutaciones críticas compartirán unidad transaccional:

```text
IdempotencyRecord
business document
InventoryReservation cuando aplique
ClassInventoryObligation/Attribution cuando aplique
InventoryMovement
InventoryBalance
audit
outbox
```

Reglas:

- un rollback revertirá todo;
- `COMPLETED` se confirmará con los efectos;
- un replay no generará movimientos adicionales;
- la constraint causal evitará duplicaciones;
- `Idempotency-Key` no será sustituida por la clave causal;
- autorización y scopes se revalidarán conforme a DEC-03 y DEC-04.

### Rendimiento

```text
ledger inmutable = fuente de causalidad
InventoryBalance = proyección operacional materializada
```

No se reconstruirá todo el ledger para cada lectura del POS. Los procesos de reconciliación podrán verificar o reconstruir balances fuera del camino síncrono. DEC-08 no fija un SLA sin baseline.

### Migración conceptual

1. Añadir `quantity_reserved` con valor inicial cero sin reinterpretar históricos.
2. Crear persistencia causal de reservas.
3. Crear obligaciones y atribuciones `CLASS_CAPTURE`.
4. Ampliar el ledger con causalidad, snapshot UOM, línea origen, idempotencia y reversas.
5. Crear constraints e índices causales.
6. Introducir locking ordenado.
7. Migrar los flujos existentes que ya escriben ledger.
8. Corregir las transferencias parciales.
9. Migrar las ventas `PRODUCT_DIRECT`.
10. Migrar la reconciliación `CLASS_CAPTURE`.
11. Migrar pedidos.
12. Unificar los flujos POS y Backoffice de transferencias y merma.
13. Integrar devoluciones y correcciones.
14. Aplicar conversiones UOM.
15. Integrar DEC-07, auditoría y outbox.
16. Actualizar OpenAPI desde backend.
17. Regenerar el cliente TypeScript.
18. Actualizar POS y Backoffice.
19. Reconciliar el balance materializado contra el ledger.

No se inventarán movimientos históricos para explicar saldos actuales. Todo backfill incierto, UOM histórico, saldo negativo existente y documento ambiguo dependerá de DEC-19.

### Pruebas futuras obligatorias

#### `PRODUCT_DIRECT`

- decremento exactamente una vez;
- stock insuficiente;
- replay;
- concurrencia.

#### `CLASS_CAPTURE`

- obligación creada;
- atribución parcial;
- atribución completa;
- sobre-atribución rechazada;
- replay;
- cierre con obligación pendiente;
- cero descuento al confirmar;
- un solo descuento al atribuir.

#### Reservas

- reserve;
- release;
- consume;
- doble release;
- doble consume;
- delivery frente a cancel.

#### Transferencias

- dispatch;
- receive;
- recepción parcial;
- recepción duplicada;
- diferencia explícita;
- merma en tránsito;
- concurrencia.

#### Producción

- start;
- complete;
- cancel antes y después de uso;
- merma;
- retorno;
- output.

#### Compras

- create sin stock;
- confirm sin stock;
- receive con stock;
- direct entry;
- conversión UOM;
- replay.

#### Reversas

- movimiento compensatorio;
- doble reversa rechazada;
- causalidad reconstruible.

#### Stock negativo

- operación ordinaria rechazada;
- ajuste excepcional autorizado;
- ajuste negativo sin razón o permiso rechazado.

#### Rendimiento

- ausencia de lock global;
- productos diferentes concurrentes;
- sucursales diferentes concurrentes;
- lectura operacional sin full ledger scan.

### Dependencias

- DEC-04: scope de sucursal.
- DEC-06: cierre y reconciliación física obligatoria.
- DEC-07: idempotencia exactamente una vez.
- DEC-09: devoluciones, merma y disposiciones.
- DEC-10: ciclo de pedidos y reservas comerciales.
- DEC-12: producción, WIP y consumo.
- DEC-19: datos históricos y backfill.

Estas decisiones posteriores no se resuelven mediante DEC-08.

### Evidencia técnica asociada

La validación estática de `ZM-FIN-003` comprobó:

- `InventoryBalance` actual sólo contiene `quantity_on_hand`;
- no existen reservas;
- `PRODUCT_DIRECT` no descuenta inventario;
- `CLASS_CAPTURE` actual no genera movimientos físicos por producto;
- los pedidos no reservan ni consumen stock;
- las transferencias POS no actualizan el ledger;
- las transferencias administrativas sí lo hacen parcialmente;
- las compras reciben a `BACKROOM`, pero no aplican consistentemente un snapshot de conversión;
- producción sólo afecta inventario al completar;
- merma POS y administrativa divergen;
- las devoluciones almacenan disposición sin efecto físico;
- los ajustes permiten negativos;
- no existe una constraint causal única ni idempotencia transversal implementada.

Estos hechos describen el código vigente y no equivalen a implementación de DEC-08.

### Consecuencias, límite e historial

- **Tareas afectadas:** `ZM-FIN-003`, `ZM-FIN-008` y las tareas posteriores del Plan Maestro que implementen inventario, ventas, pedidos, transferencias, producción, compras, devoluciones, merma, contratos y migración de datos.
- **Consecuencias:** nuevo modelo de reservas y obligaciones, ampliación del ledger, locking ordenado, integración con DEC-07, contratos backend-first, regeneración del cliente TypeScript, adopción coordinada por POS y Backoffice y pruebas de causalidad, atomicidad, concurrencia y rendimiento.
- **Límite:** DEC-08 define la política y el modelo conceptual; no certifica que ledger, reservas, obligaciones, movimientos, locking, migraciones, contratos, clientes o pruebas estén implementados.
- **Historial:** `PENDIENTE` desde 2026-08-26; `APROBADA` por el propietario el 2026-08-27.

## DEC-09 — Devolución y merma

- **Estado:** `APROBADA`
- **Fecha:** 2026-08-27
- **Propietario:** propietario de ZeroMerma
- **Contenido aprobado:** causalidad, inmutabilidad, disposiciones físicas, cuarentena, split disposition, conservación del derecho de devolución, locking, devoluciones `CLASS_CAPTURE`, merma, compensaciones, sucursal, rendimiento, migración y pruebas futuras.
- **Respuesta aprobada:** política normativa, modelos conceptuales, invariantes, dependencias y pruebas futuras descritos en esta decisión.

### Principio general

Toda devolución y toda merma comprometida será:

```text
causal
inmutable
auditable
idempotente
compatible con DEC-06, DEC-07 y DEC-08
```

La realidad financiera, documental y física permanecerá relacionada causalmente, pero no se considerará automáticamente equivalente.

### Disposiciones aprobadas

Las disposiciones canónicas serán:

```text
RESTOCK_COUNTER
RESTOCK_BACKROOM
QUARANTINE
SEND_TO_WASTE
NO_STOCK
```

#### `RESTOCK_COUNTER`

Sólo podrá utilizarse cuando el producto:

- sea inventariable;
- esté identificado físicamente;
- esté íntegro;
- sea apto para venta directa.

Su efecto será:

```text
producto retornado
-> InventoryMovement IN
-> COUNTER
```

#### `RESTOCK_BACKROOM`

Sólo podrá utilizarse cuando el producto:

- sea inventariable;
- sea físicamente recuperable;
- pueda mantenerse como existencia;
- no necesite volver inmediatamente a mostrador.

Su efecto será:

```text
producto retornado
-> InventoryMovement IN
-> BACKROOM
```

#### `QUARANTINE`

Será la disposición segura por defecto cuando exista duda material sobre:

- calidad;
- integridad;
- daño;
- condición sanitaria;
- aptitud para venta o producción.

Sus invariantes serán:

```text
tracked_physical_quantity=true
sellable=false
reservable=false
production_eligible=false
automatic_release=false
```

Una operación posterior explícita y autorizada podrá mover el producto desde `QUARANTINE` hacia:

```text
COUNTER
BACKROOM
WASTE
```

No existirá liberación automática.

#### `SEND_TO_WASTE`

Representará producto devuelto que:

```text
no es vendible
se considera descartado
queda destinado a merma
```

La devolución materializará el efecto físico correspondiente exactamente una vez.

#### `NO_STOCK`

Sólo será válido cuando el producto identificado realmente no esté sujeto a control de inventario. Requerirá:

```text
product_id concreto
Product.is_inventory_tracked=false
reason obligatorio
audit
```

Se rechazará para productos inventariables y no podrá utilizarse para ocultar una inconsistencia de inventario.

### Compatibilidad de `QUARANTINE` con DEC-08

DEC-08 permanece sin cambios:

```text
arithmetic_available =
on_hand - reserved
```

Para `QUARANTINE` se aplicará adicionalmente elegibilidad operacional por ubicación:

```text
QUARANTINE.is_sellable=false
QUARANTINE.is_reservable=false
QUARANTINE.is_production_eligible=false

effective_available_for_operation=0
```

Esto no redefine el balance aritmético de DEC-08. `QUARANTINE` conserva existencia física trazada, pero no es fuente elegible para venta, reserva ni producción.

Como regla general:

```text
QUARANTINE.quantity_reserved=0
```

Una reserva existente deberá resolverse explícitamente antes de mover el producto a cuarentena.

### Modelo canónico de devolución

La estructura conceptual recomendada será:

```text
SaleReturn
  original_sale_id
  branch_id
  financial/cash context
  reason
  actor
  committed_at
```

```text
SaleReturnLine
  sale_return_id
  original_sale_line_id
  quantity
  refund snapshot
  UOM snapshot
```

```text
ReturnDispositionAllocation
  return_line_id
  product_id
  quantity_base
  source_quantity
  source_uom
  conversion_factor
  disposition
  target_location nullable
  causal_effect_code
  idempotency_record_id
```

La forma física exacta podrá variar durante la implementación, pero deberá preservar esta separación:

```text
línea económica de devolución
!=
una única disposición física obligatoria
```

Este modelo permitirá split disposition sin duplicar el refund.

### Split disposition

Una misma cantidad devuelta podrá distribuirse entre varias disposiciones.

Ejemplo:

```text
SaleReturnLine:
  quantity=4

Allocation A:
  product X
  quantity=2
  RESTOCK_BACKROOM

Allocation B:
  product X
  quantity=1
  QUARANTINE

Allocation C:
  product X
  quantity=1
  SEND_TO_WASTE
```

Invariantes:

```text
return_line.quantity > 0
allocation.quantity > 0

sum(allocation.quantity)
=
return_line.quantity
```

Cada allocation tendrá un efecto causal independiente y exactamente una vez. Dividir la realidad física no duplicará el refund.

### Conservación del derecho de devolución

Por cada línea original:

```text
net_committed_returns
<=
original_sold_quantity
```

Conceptualmente:

```text
net_committed_returns =
committed_return_quantity
-
explicit_entitlement_restoring_compensations
```

Reglas:

- toda validación será transaccional;
- la línea original o una proyección de entitlement se bloqueará;
- la cantidad retornable se recalculará bajo lock;
- dos devoluciones concurrentes no podrán devolver la misma unidad.

No restaurarán automáticamente el derecho de devolución:

```text
reversa puramente financiera
InventoryMovement reversal aislada
cambio administrativo de status
corrección de datos maestros
```

Sólo una compensación causal explícita que restaure ese derecho podrá disminuir `net_committed_returns`.

### Locking y concurrencia

El orden conceptual será equivalente a:

```text
1. IdempotencyRecord
2. Sale/SaleLine o entitlement correspondiente
3. CashSession cuando exista efecto financiero de caja
4. InventoryBalance ordenados según DEC-08
5. ClassInventoryObligation/Attribution cuando aplique
6. efectos
7. commit único
```

Los balances se ordenarán determinísticamente mediante una clave equivalente a:

```text
branch_id
product_id
location_code
```

Resultados normativos:

```text
no_global_return_lock=true
return_quantity_race_safe=true
different_sales_can_progress_concurrently=true
different_branches_can_progress_concurrently=true
```

Ante dos devoluciones concurrentes por la última unidad retornable:

```text
una completa
la otra recalcula
la otra falla con RETURN_QUANTITY_EXCEEDED
```

No será válida una comprobación optimista en memoria sin protección transaccional sobre la cantidad retornable.

### `RESTOCK`

Para `RESTOCK_COUNTER` y `RESTOCK_BACKROOM`, cada allocation producirá:

```text
InventoryMovement IN
+
quantity_on_hand += quantity
```

en la ubicación correspondiente.

El efecto:

- tendrá causalidad;
- conservará UOM snapshot;
- quedará relacionado con devolución, línea y allocation;
- será idempotente;
- sucederá exactamente una vez;
- compartirá unidad transaccional con los efectos internos correspondientes.

No se creará un decremento ficticio anterior sólo para justificar el restock.

### `QUARANTINE`

`QUARANTINE` será una ubicación física explícita no elegible.

Una liberación posterior requerirá:

```text
QUARANTINE OUT
+
COUNTER | BACKROOM | WASTE IN
```

mediante una nueva operación autorizada, causal, auditada e idempotente. La disposición histórica original no se modificará.

### `SEND_TO_WASTE` desde devolución

La representación preferida será una entrada física directa desde el cliente o contexto externo a `WASTE`:

```text
cliente/exterior
-> InventoryMovement IN WASTE
```

Esto producirá:

```text
returned_physical_item=true
sellable_stock_increment=0
waste_quantity_increment=true
```

No se creará un ingreso artificial a `COUNTER` o `BACKROOM` para retirarlo inmediatamente.

Si el material permanece físicamente bajo custodia:

```text
WASTE = ubicación física no vendible
```

La eliminación terminal posterior podrá registrarse mediante:

```text
InventoryMovement OUT WASTE
```

Si devolución y eliminación física terminal ocurren materialmente en el mismo acto, podrán expresarse como efectos causales pareados del mismo documento sin pasar por una ubicación vendible.

### `SEND_TO_WASTE` y transacción de devolución

Cuando todos los efectos sean internos y terminales:

```text
return
refund interno
allocation SEND_TO_WASTE
InventoryMovement
balance
audit
outbox
IdempotencyRecord
```

compartirán una unidad transaccional. No se requerirá una segunda tarea manual de merma para materializar el mismo retorno físico.

Esto no implica una transacción distribuida con un proveedor de pagos externo. Los refunds externos permanecen como dependencia de DEC-14.

### `CLASS_CAPTURE`

Para devolver físicamente una unidad originada en `CLASS_CAPTURE` será obligatorio identificar un:

```text
product_id concreto
```

No existirá:

```text
restock de clase genérica
waste de clase genérica
quarantine de clase genérica
```

#### Venta totalmente atribuida

El SKU:

- deberá pertenecer a la clase;
- deberá estar respaldado por atribuciones causales de la venta;
- no podrá devolverse por encima de la cantidad atribuida neta de retornos previos.

#### Venta pendiente o parcialmente atribuida

La devolución podrá, dentro de la misma transacción:

```text
atribuir SKU a la obligación original
+
crear movimiento causal de la venta
+
crear allocation de devolución
+
crear efecto físico de la disposición
```

Son dos hechos distintos:

```text
atribución original:
explica qué salió en la venta

devolución:
explica qué regresó y cuál fue su disposición
```

No se considerará doble movimiento si ambos hechos están causalmente identificados.

Ejemplo:

```text
atribución original:
COUNTER -1

devolución RESTOCK_COUNTER:
COUNTER +1
```

El neto físico será cero, pero conservará causalidad completa. Si no puede demostrarse un SKU válido sin violar DEC-08, no se inventará.

### `NO_STOCK`

`NO_STOCK` sólo podrá utilizarse cuando:

```text
Product.is_inventory_tracked=false
```

y exista:

```text
reason
actor
audit/outbox
```

No generará `InventoryMovement`. Para un producto inventariable se rechazará mediante un error estable equivalente a:

```text
RETURN_NO_STOCK_NOT_ALLOWED
```

### Inmutabilidad

Una devolución comprometida será inmutable. Una merma comprometida será inmutable.

No se permitirá:

```text
editar cantidad histórica
cambiar disposición histórica
borrar devolución
borrar merma
borrar movimiento para cuadrar
```

Toda corrección utilizará:

```text
nuevo documento compensatorio
referencia causal al original
reason
actor
audit
outbox
idempotency
```

### Modelo de reversas y compensaciones

Se distinguirán conceptualmente:

```text
ReturnCompensation
FinancialRefundCompensation
InventoryMovement reversal
WasteDisposition correction
```

Los nombres físicos podrán variar durante la implementación.

#### Return compensation

Corregirá causalmente el documento de devolución. Sólo restaurará el derecho de devolución si declara y sustenta explícitamente ese efecto.

#### Financial refund compensation

Corregirá dinero. Por sí sola:

```text
no restaura inventario
no restaura entitlement
```

#### Inventory movement reversal

Creará un nuevo movimiento físico opuesto. No alterará automáticamente el refund ni el documento.

#### Waste disposition correction

Si el producto todavía existe físicamente y puede recuperarse, será una nueva disposición autorizada desde `WASTE`.

### Reversa de `WASTE`

Una reversa financiera o documental no producirá automáticamente:

```text
WASTE -> COUNTER
WASTE -> BACKROOM
```

La realidad física sólo cambiará mediante una disposición posterior explícita.

Regla:

```text
refund reversed
!=
inventory automatically sellable
```

### Merma canónica

POS y Backoffice podrán mantener UIs distintas, pero convergerán a la misma semántica de dominio:

```text
same_domain_effect=true
same_inventory_causality=true
```

El protocolo conceptual `commit_waste(...)` requerirá:

- producto concreto;
- cantidad;
- ubicación origen;
- reason;
- capability;
- scope de sucursal;
- disponibilidad;
- locking DEC-08;
- documento;
- movimiento causal;
- balance;
- audit;
- outbox;
- idempotencia;
- commit único.

### Representación de `WASTE`

`WASTE` podrá funcionar como ubicación física no vendible mientras el material permanezca bajo custodia.

Una merma desde una ubicación vendible podrá representarse como:

```text
source location OUT
+
WASTE IN
```

Cuando el descarte físico terminal ocurra inmediatamente y la arquitectura lo represente expresamente, podrá existir una disposición terminal equivalente, preservando siempre la causalidad.

POS y Backoffice no conservarán consecuencias físicas distintas.

### Capabilities y alto impacto

Se utilizarán las capabilities ya aprobadas:

```text
returns_corrections.manage
waste.manage
```

DEC-09 no amplía el catálogo de DEC-03.

Política:

- capability correspondiente;
- reason;
- audit;
- no existirá un segundo aprobador universal;
- un segundo aprobador sólo se exigirá cuando exista una regla o umbral futuro explícitamente aprobado.

DEC-09 no fija importes, porcentajes, cantidades ni umbrales nuevos.

### Sucursal

La política ordinaria será:

```text
return.branch_id == original_sale.branch_id
```

Una devolución cross-branch no estará habilitada ordinariamente. Hasta que exista un flujo explícito:

```text
ordinary_cross_branch_return=false
```

El futuro flujo deberá definir:

- sucursal receptora física;
- ledger;
- compensación financiera;
- caja;
- scopes de ambos extremos;
- auditoría.

El error conceptual estable será:

```text
RETURN_CROSS_BRANCH_NOT_ALLOWED
```

La política se aplicará en backend conforme a DEC-04.

### Relación con DEC-06

Si la devolución produce un refund interno asociado a una caja:

- adquirirá la frontera de `CashSession`;
- validará `OPEN`;
- registrará el `CashMovement` dentro de esa unidad transaccional;
- no podrá quedar fuera del cierre.

Si la caja histórica está cerrada:

```text
no reopen
no edit original close
```

El desembolso pertenecerá a una caja abierta autorizada o a un documento financiero compensatorio adecuado. La recepción física del producto no reabrirá la caja histórica.

### Relación con DEC-07

Como mínimo requerirán idempotencia códigos equivalentes a:

```text
return.commit
waste.commit
return.compensate
waste.compensate
quarantine.release
```

Un replay `COMPLETED` garantizará:

```text
duplicate refund=0
duplicate InventoryMovement=0
duplicate waste effect=0
duplicate audit business effect=0
duplicate outbox business effect=0
```

La causal unique del ledger complementará DEC-07 y no sustituirá la `Idempotency-Key`.

### Relación con DEC-08

DEC-09 preserva:

```text
movimientos inmutables
UOM snapshot
balances materializados
causal uniqueness
reversas compensatorias
locking ordenado
stock negativo ordinario prohibido
exactly once
```

DEC-09 utiliza el modelo de inventario de DEC-08 y no crea un segundo ledger.

### Dependencias posteriores

#### DEC-11

Permanecen pendientes:

- devolución de pago mixto;
- reparto del refund entre medios;
- límites y redondeos por medio.

#### DEC-14

Permanecen pendientes:

- refund externo;
- `PROCESSING`;
- `UNKNOWN`;
- conciliación con procesador o adquirente.

#### DEC-19

Permanecen pendientes:

- datos históricos;
- movimientos históricos inexistentes;
- disposiciones antiguas sin efecto físico;
- reconciliación y backfill.

Un proveedor externo no participará en una transacción SQL distribuida.

### Errores conceptuales estables

Se definirán errores equivalentes a:

```text
RETURN_QUANTITY_EXCEEDED
RETURN_DISPOSITION_REQUIRED
RETURN_DISPOSITION_SUM_MISMATCH
RETURN_PRODUCT_REQUIRED
RETURN_PRODUCT_CLASS_MISMATCH
RETURN_NO_STOCK_NOT_ALLOWED
RETURN_CROSS_BRANCH_NOT_ALLOWED
RETURN_ALREADY_COMPENSATED
WASTE_INSUFFICIENT_STOCK
WASTE_ALREADY_COMPENSATED
QUARANTINE_NOT_SELLABLE
```

Semántica general:

```text
409:
conflictos con estado actual/recurso/concurrencia

422:
input o disposición semánticamente inválidos
```

DEC-09 no implementa estos contratos.

### Auditoría y outbox

Los eventos conceptuales serán equivalentes a:

```text
return.committed
return.disposition_recorded
return.compensated
waste.committed
waste.compensated
quarantine.released
```

No será obligatorio utilizar exactamente esos nombres si la convención de implementación justifica otros.

Los datos auditables mínimos serán:

```text
actor
branch_id
sale_id
sale_line_id
return_id
allocation_id
product_id
quantity
UOM
disposition
source_location
target_location
reason
financial_effect/reference
request_id
idempotency reference no secreta
timestamp
```

Un replay no generará un nuevo efecto de negocio.

### Rendimiento y concurrencia

Resultados normativos:

```text
no_global_return_lock=true
no_global_waste_lock=true
full_inventory_ledger_scan_per_return=false
full_return_history_scan=false
different_sales_can_progress_concurrently=true
different_branches_can_progress_concurrently=true
```

Las consultas de cantidades retornables y compensaciones utilizarán índices adecuados. DEC-09 no fija un SLA sin baseline.

### Migración conceptual

1. Añadir `QUARANTINE`.
2. Añadir `NO_STOCK`.
3. Añadir elegibilidad de `QUARANTINE`.
4. Separar `SaleReturnLine` de las allocations físicas.
5. Migrar cada línea histórica actual a una allocation única usando exclusivamente su disposición existente demostrable.
6. No inventar split histórico.
7. Crear locking transaccional de entitlement.
8. Crear efectos físicos para devoluciones nuevas.
9. No inventar movimientos de inventario históricos ambiguos.
10. Integrar `CLASS_CAPTURE` con DEC-08.
11. Crear documentos compensatorios.
12. Integrar DEC-07.
13. Aplicar la frontera DEC-06 para refunds internos.
14. Unificar la semántica de merma POS y Backoffice.
15. Representar `WASTE` causalmente.
16. Aplicar capabilities y scopes DEC-03/04.
17. Actualizar OpenAPI backend-first.
18. Regenerar el cliente TypeScript.
19. Actualizar POS y Backoffice.
20. Reconciliar históricos mediante DEC-19.

### Evidencia técnica asociada

La validación estática de `ZM-FIN-003` comprobó:

- `SaleReturnLine` actual contiene una sola disposición;
- split disposition no existe;
- no existe `QUARANTINE`;
- no existe `NO_STOCK`;
- la cantidad retornada se valida actualmente sin locking transaccional suficiente;
- `RESTOCK_COUNTER` y `RESTOCK_BACKROOM` no generan un ledger real;
- `SEND_TO_WASTE` sólo registra disposición y no materializa inventario;
- `CLASS_CAPTURE` exige SKU concreto, pero todavía no integra las obligaciones de DEC-08;
- los refunds crean `CashMovement`, pero todavía no adquieren la frontera DEC-06;
- la merma POS no actualiza inventario;
- la merma Backoffice sí decrementa parcialmente el origen;
- no existe una reversa canónica;
- no existe idempotencia DEC-07 transversal;
- cross-branch ordinario ya está rechazado por la lógica actual, aunque faltan los guards definitivos de DEC-04.

Estos hechos describen el código vigente y no equivalen a implementación de DEC-09.

### Pruebas futuras obligatorias

#### Cantidades

- devolución parcial;
- devolución total;
- sobredevolución;
- dos devoluciones concurrentes;
- replay.

#### Disposiciones

- counter;
- backroom;
- quarantine;
- waste;
- no-stock válido;
- no-stock inválido;
- split.

#### `CLASS_CAPTURE`

- totalmente reconciliado;
- pendiente;
- SKU inválido;
- atribución y devolución en una transacción;
- cero doble efecto.

#### `QUARANTINE`

- existencia física rastreada;
- no vendible;
- no reservable;
- no utilizable en producción;
- liberación explícita.

#### Merma

- POS;
- Backoffice;
- misma causalidad;
- exactly once;
- stock insuficiente.

#### Reversas

- compensación documental;
- compensación financiera;
- movimiento físico compensatorio;
- ausencia de auto-restock desde `WASTE`;
- doble compensación rechazada.

#### Sucursal

- misma sucursal;
- cross-branch rechazado.

#### Atomicidad e idempotencia

- crash antes de commit;
- respuesta perdida;
- refund exactly once;
- inventory exactly once;
- audit exactly once;
- outbox exactly once.

#### Concurrencia y rendimiento

- diferentes ventas en paralelo;
- diferentes productos;
- diferentes sucursales;
- ausencia de locks globales;
- ausencia de full scans.

### Dependencias

- DEC-04: scopes y sucursal.
- DEC-06: `CashSession` y cierre.
- DEC-07: idempotencia.
- DEC-08: ledger, balances, UOM y locking.
- DEC-11: mixed-payment refund.
- DEC-14: refund externo, `PROCESSING` y `UNKNOWN`.
- DEC-19: históricos y backfill.

Estas dependencias no se resuelven mediante DEC-09.

### Consecuencias, límite e historial

- **Tareas afectadas:** `ZM-FIN-003`, `ZM-FIN-008` y las tareas posteriores del Plan Maestro que implementen devoluciones, correcciones, merma, inventario, caja, contratos y migración de datos.
- **Consecuencias:** allocations físicas separadas, nueva ubicación `QUARANTINE`, locking de entitlement, integración con DEC-06/07/08, merma canónica, compensaciones, contratos backend-first, regeneración de cliente y pruebas de causalidad, atomicidad, concurrencia y rendimiento.
- **Límite:** DEC-09 define la política y el modelo conceptual; no certifica que devoluciones, merma, cuarentena, allocations, movimientos, locking, idempotencia, migraciones, contratos, clientes o pruebas estén implementados.
- **Historial:** `PENDIENTE` desde 2026-08-26; `APROBADA` por el propietario el 2026-08-27.

## DEC-10 — Pedidos

- **Estado:** `APROBADA`
- **Fecha:** 2026-08-28
- **Propietario:** propietario de ZeroMerma
- **Contenido aprobado:** naturaleza económica, anticipo mínimo, pagos, snapshot, producto exacto, ciclo, reservas, entrega, reconocimiento de ingreso, amendments, frontera comercial `PRODUCTION_COMMITTED`, cancelación, expiración, sucursal, caja, locking, rendimiento, migración y pruebas futuras.
- **Respuesta aprobada:** política normativa, modelos conceptuales, invariantes, dependencias y pruebas futuras descritos en esta decisión.

### Revisión vigente — 2026-08-28

#### Sustitución de la frontera de cancelación

La versión inicial de DEC-10, aprobada el 2026-08-28, utilizó `production_started` como frontera ordinaria para determinar el refund de una cancelación atribuible al cliente.

Evidencia operativa posterior suministrada por el propietario estableció que:

- los panaderos no realizan captura digital rutinaria;
- producción opera principalmente mediante un monitor de sólo lectura;
- ZeroMerma debe funcionar completamente sin sensores ni instrumentación avanzada;
- no existe una señal confiable y obligatoria de inicio físico de producción.

Exigir `production_started` como autoridad financiera obligaría a introducir captura rutinaria o instrumentación que la operación aprobada no garantiza. Por ello, queda sustituida exclusivamente esa frontera por el milestone comercial y de planificación:

```text
PRODUCTION_COMMITTED
```

Desde esta revisión, las cláusulas vigentes de DEC-10 son las que utilizan `PRODUCTION_COMMITTED`. Las referencias históricas a `production_started` documentan la versión inicial, pero no constituyen política vigente.

Las demás reglas de DEC-10 permanecen aprobadas y sin cambio, incluyendo anticipo mínimo, producto exacto, ciclo del pedido, reserva completa, entrega, reconocimiento de ingreso, sucursal, caja, idempotencia y relaciones con DEC-06 a DEC-11.

La dimensión comercial queda conceptualmente:

```text
PENDING + NOT_COMMITTED
PENDING + PRODUCTION_COMMITTED
READY
DELIVERED
```

`PRODUCTION_COMMITTED` será un milestone comercial irreversible y no necesita ser un estado principal de `CustomerOrder`.

### Naturaleza económica del pedido

Un pedido confirmado representa inicialmente un compromiso comercial, no una venta entregada.

La confirmación:

- congela su snapshot comercial vigente;
- registra los anticipos o pagos recibidos;
- no reconoce todavía el ingreso total como venta entregada.

El ingreso de la venta se reconocerá únicamente cuando el pedido alcance:

```text
DELIVERED
```

Los anticipos y liquidaciones recibidos antes de `DELIVERED`:

- serán movimientos financieros reales;
- pertenecerán a la caja y turno donde fueron cobrados;
- participarán en el cierre de esa caja conforme a DEC-06;
- permanecerán distinguibles del ingreso de una venta entregada.

Regla normativa:

```text
cash_received_before_delivery
!=
sale_revenue_recognized
```

DEC-10 no define un libro contable general.

### Anticipo obligatorio del 50 %

La política será aplicada por backend:

```text
minimum_advance_percent = 50%
```

Para confirmar un pedido:

```text
minimum_advance =
quantize(order_total_snapshot * 0.50, 0.01, ROUND_HALF_UP)
```

Esta regla reutiliza la escala y el redondeo monetario vigentes.

Ejemplo normativo:

```text
order_total=33.33
50%=16.665
minimum_advance=16.67
```

Invariantes:

```text
net_paid >= minimum_advance
net_paid <= order_total
```

El sistema:

- calculará automáticamente el anticipo mínimo;
- lo mostrará a la cajera;
- impedirá en backend confirmar por debajo del mínimo;
- no concederá una excepción discrecional a la cajera;
- no permitirá que un pedido confirmado persista durablemente por debajo del 50 %;
- no permitirá sobrepago.

Un borrador puramente local de UI no constituirá un pedido confirmado.

### Pagos posteriores

Después del anticipo inicial podrán existir múltiples pagos adicionales.

Regla permanente:

```text
0 <= net_paid <= order_total
```

Cada pago:

- será causal e idempotente;
- estará vinculado al pedido;
- identificará la caja y turno donde se recibió;
- podrá pertenecer a un turno distinto del anticipo inicial;
- no reconocerá por sí solo ingreso de venta;
- producirá el efecto financiero que DEC-06 incluirá en cash close.

El reparto entre medios y el pago mixto pertenecen a DEC-11. Los pagos externos pertenecen a DEC-14.

### Protección contra sobrepago

`net_paid` deberá mantenerse mediante una proyección o materialización race-safe respaldada por el subledger financiero.

Dos pagos concurrentes nunca podrán producir:

```text
net_paid > order_total
```

La validación se realizará bajo el lock del agregado del pedido.

Ejemplo:

```text
total=1000
paid=900

T1 intenta +100
T2 intenta +100

T1 bloquea el pedido y confirma net_paid=1000
T2 adquiere después el lock
T2 recalcula y se rechaza
```

### Snapshot comercial

Cada versión confirmada del pedido preservará como mínimo:

```text
product_id
product name/description snapshot cuando corresponda
quantity
unit_price_snapshot
line_total_snapshot
discount/promotion snapshot cuando DEC-13 aplique
order_total_snapshot
minimum_advance_policy/version
cancellation_policy/version
production_commit_policy/version
production_commit_at UTC
branch timezone/offset snapshot usado para el cálculo
fulfillment_branch_id
effective timestamp/version
```

Cambios posteriores de catálogo, precio, promoción o política no recalcularán silenciosamente pedidos confirmados.

DEC-13 determinará el cálculo inicial de precios, promociones y descuentos. DEC-10 congela el resultado aplicado.

### Productos siempre exactos

Todo pedido utilizará un producto exacto:

```text
CustomerOrderItem.product_id = obligatorio
```

Los pedidos no utilizarán `CLASS_CAPTURE`. Una clase será exclusivamente un mecanismo de navegación o presentación.

Ejemplo:

```text
Conchas
  -> Concha vainilla
  -> Concha chocolate
  -> Concha fresa
```

Antes de añadir una línea se seleccionará un producto o SKU concreto.

No se persistirán como identidad física de una línea de pedido:

```text
product_class_id genérico
cantidad CLASS_CAPTURE
ClassInventoryObligation
```

`ClassInventoryObligation` de DEC-08 pertenece a ventas `CLASS_CAPTURE`, no a pedidos.

### Máquina de estados

Estados canónicos:

```text
PENDING
READY
DELIVERED
CANCELED
EXPIRED
NO_SHOW
```

Transiciones permitidas:

```text
PENDING -> READY
PENDING -> CANCELED
PENDING -> EXPIRED
PENDING -> NO_SHOW

READY -> DELIVERED
READY -> CANCELED
READY -> EXPIRED
READY -> NO_SHOW
```

Estados terminales:

```text
DELIVERED
CANCELED
EXPIRED
NO_SHOW
```

Transiciones prohibidas:

```text
READY -> PENDING
PENDING -> DELIVERED
DELIVERED -> CANCELED
DELIVERED -> READY
```

No habrá transiciones silenciosas causadas únicamente por el paso del tiempo. Después de `DELIVERED`, las devoluciones y correcciones pertenecen a DEC-09.

### `READY` y reserva completa

Conforme a DEC-08:

```text
READY -> reserve exact products
```

La separación vigente será:

```text
PRODUCTION_COMMITTED = frontera comercial y de planificación
READY                 = producto preparado y reserva completa para entrega
DELIVERED             = entrega y reconocimiento de ingreso
```

`READY` no sustituye, crea ni modifica retroactivamente el commitment. Una transición a `READY` anterior a `production_commit_at` no podrá cerrar silenciosamente la ventana de cancelación y deberá rechazarse o diferirse según la implementación posterior.

DEC-10 fija:

```text
full reservation or fail
```

No se soportarán inicialmente:

```text
partial reservation
implicit backorder
partial READY
```

Protocolo conceptual:

```text
lock order
require PENDING
lock balances/reservations
validate complete availability
create all reservations exactly once
status=READY
audit/outbox/idempotency
commit
```

Si una sola línea carece de disponibilidad:

```text
ORDER_READY_STOCK_INSUFFICIENT
```

y el resultado será:

```text
pedido permanece PENDING
reservas parciales comprometidas = 0
```

### `DELIVERED`

Sólo podrá comprometerse cuando:

```text
status=READY
net_paid=order_total
reservations complete
```

El pedido podrá haberse pagado completamente antes o podrá cobrarse el saldo final en la misma unidad transaccional de entrega.

Al comprometer `DELIVERED`:

```text
consume reservation exactly once
recognize order_total_snapshot revenue exactly once
mark DELIVERED
audit
outbox
idempotency COMPLETED
```

Efecto físico conforme a DEC-08:

```text
quantity_on_hand -= reserved quantity
quantity_reserved -= reserved quantity
```

### Sin entrega parcial

La entrega parcial no estará soportada inicialmente:

```text
partial delivery unsupported
```

No existirán:

```text
PARTIALLY_DELIVERED
partial reservation consumption
partial revenue recognition by delivery
```

El pedido se entregará completo o permanecerá `READY`. Un flujo parcial futuro requerirá una decisión explícita.

### Reconocimiento de ingreso

El subledger del pedido distinguirá conceptos equivalentes a:

```text
ADVANCE_RECEIVED
SETTLEMENT_RECEIVED
REFUND
REVENUE_RECOGNIZED
```

Regla:

```text
cash receipt at payment time
revenue recognition at DELIVERED
```

Al entregar:

```text
recognized_revenue = order_total_snapshot
exactly_once=true
```

No se creará una `Sale` ficticia ligada a una única `CashSession` para representar un pedido cuyos pagos puedan abarcar varios turnos.

Una cancelación anterior a `DELIVERED` tendrá:

```text
sale revenue recognized = 0
```

Si una cancelación del cliente ocurre después de `PRODUCTION_COMMITTED` y se retiene el dinero:

```text
retained advance
!=
DELIVERED sale revenue
```

DEC-10 no reclasifica silenciosamente ese importe como una venta entregada. Su clasificación contable posterior deberá resolverse explícitamente si se requiere.

### Modificaciones mientras `PENDING`

Mientras el pedido esté `PENDING` podrá utilizarse una operación equivalente a:

```text
order.amend
```

La operación será auditada e idempotente y conservará historial mediante versiones o snapshots equivalentes.

Sólo podrá confirmarse mientras `PRODUCTION_COMMITTED` todavía no sea efectivo. La transacción deberá bloquear el pedido, validar la versión vigente y conservar el orden histórico completo.

Cada nueva versión confirmada anterior al commitment:

- recalculará prospectivamente `production_commit_at` mediante la política aplicable;
- mostrará el nuevo cutoff antes de su confirmación;
- conservará el cutoff y snapshot de la versión anterior;
- generará una nueva identidad estable de commitment;
- no podrá establecer un cutoff retrospectivo anterior al momento de confirmación del amendment.

Después del amendment:

```text
net_paid >= 50% new_total
net_paid <= new_total
```

Si el total aumenta y se obtiene:

```text
net_paid < 50% new_total
```

la nueva versión no podrá confirmarse sin completar simultáneamente el anticipo requerido o mediante una operación compuesta equivalente.

Si el total disminuye y se obtiene:

```text
net_paid > new_total
```

la modificación se rechazará salvo que una operación financiera explícita y atómica resuelva el exceso. No se generarán refunds silenciosos.

Después de que `PRODUCTION_COMMITTED` sea efectivo, `order.amend` será rechazado con un código equivalente a:

```text
ORDER_AMENDMENT_AFTER_PRODUCTION_COMMITMENT
```

No se permitirá borrar el milestone, modificar su `effective_at`, desplazar el cutoff para recuperar un derecho perdido ni reactivar una versión anterior.

Después de `READY` continuarán bloqueados:

```text
product_id
quantity
price snapshot
order total
```

Un cambio posterior requerirá cancelación y recreación o un futuro workflow explícito de amendment.

### Semántica vigente de `PRODUCTION_COMMITTED`

`PRODUCTION_COMMITTED` significa:

- el pedido quedó formalmente comprometido al plan productivo;
- terminó la ventana ordinaria de cancelación con reembolso para el cliente;
- la panadería puede haber comprometido capacidad productiva planificada.

No significa:

- inicio físico real;
- captura del panadero;
- movimiento de inventario;
- WIP;
- consumo de insumos;
- output o merma;
- producto terminado;
- `READY`.

Invariantes:

```text
PRODUCTION_COMMITTED != production_started
PRODUCTION_COMMITTED != READY
PRODUCTION_COMMITTED != WIP
PRODUCTION_COMMITTED != inventory movement
```

### Cancelación solicitada por cliente antes del commitment

Cuando:

```text
cancellation_responsibility=CUSTOMER
PRODUCTION_COMMITTED todavía no es efectivo
```

aplicará:

```text
refund = 100% net_paid
recognized_delivered_sale_revenue = 0
status = CANCELED
```

Si existen reservas se liberará la reserva restante exactamente una vez.

No se retendrá automáticamente el 50 %. El anticipo obligatorio es un requisito de confirmación, no una penalización automática.

### Cancelación solicitada por cliente después del commitment

Cuando:

```text
cancellation_responsibility=CUSTOMER
PRODUCTION_COMMITTED ya es efectivo
```

aplicará por defecto:

```text
refund = 0
status = CANCELED
recognized_delivered_sale_revenue = 0
```

No se inventarán porcentajes intermedios, penalizaciones adicionales ni refunds parciales automáticos.

El dinero retenido permanecerá financieramente distinguible y auditable y no se convertirá silenciosamente en ingreso de una venta `DELIVERED`.

### Cancelación atribuible a la panadería

Cuando:

```text
cancellation_responsibility=MERCHANT
```

aplicará:

```text
refund = 100% net_paid
recognized_delivered_sale_revenue = 0
status = CANCELED
```

La misma regla aplicará independientemente de `PRODUCTION_COMMITTED`, inicio físico, producción parcial o producto terminado.

Se registrarán:

```text
responsibility
reason
actor
decision_at
commitment evidence cuando corresponda
refund reference
```

DEC-10 no fija un catálogo exhaustivo de causas.

Un pedido `DELIVERED` no se cancela. Una devolución o corrección posterior utiliza DEC-09.

### Política de cancelación y planificación congelada

Cada versión confirmada del pedido permitirá reconstruir una política equivalente a:

```text
minimum_advance_percent = 50%

customer_cancel_before_production_commitment =
FULL_REFUND

customer_cancel_after_production_commitment =
NO_REFUND

merchant_attributable_cancel =
FULL_REFUND
```

Cada versión conservará obligatoriamente un valor equivalente a:

```text
production_commit_at
```

Será inmutable dentro de la versión, visible antes de confirmar el pedido o amendment, almacenado como instante UTC, calculado mediante una política configurada y versionada e independiente de sensores, scheduler o actividad del panadero.

El snapshot conservará como mínimo:

```text
policy_id/version
fulfillment_branch_id
branch_timezone
timezone offset aplicado
requested_for_at
inputs relevantes de producto/tipo de pedido
cutoff local calculado
production_commit_at UTC
calculation version
confirmed_at
```

DEC-10 no aprueba un lead time numérico. Si no existe una política aplicable válida, el pedido no podrá confirmarse inventando un cutoff. Cambios posteriores de configuración, política o timezone no modificarán pedidos históricos.

### Evento durable `order.production_committed`

El commitment se materializará exactamente una vez mediante un evento o milestone durable equivalente a:

```text
order.production_committed
  order_id
  order_version
  fulfillment_branch_id
  production_commit_at
  effective_at
  recorded_at
  policy_id/version
  system_actor autorizado
  idempotency reference no secreta
  causal_effect_code
```

La persistencia deberá imponer una constraint causal equivalente a:

```text
UNIQUE(order_id, order_version, causal_effect_code)
```

o una estructura técnicamente equivalente que garantice un único milestone por versión.

Semántica:

```text
effective_at = momento contractual en que cerró la ventana
recorded_at  = momento en que ZeroMerma persistió el milestone
```

La autoridad comercial es `effective_at`, no la puntualidad del scheduler.

### Scheduler y materialización oportunista

El milestone podrá materializarse mediante scheduler o worker, comando interno o materialización oportunista dentro de cancelación, `READY` u otra operación relevante.

Si una cancelación llega después de `production_commit_at` y el milestone todavía no fue persistido, la misma transacción deberá materializarlo primero con `effective_at=production_commit_at` y resolver después el refund.

Invariantes:

```text
scheduler atrasado != ventana extendida
recorded_at tardío != effective_at tardío
```

Una caída temporal del scheduler no extenderá el derecho del cliente.

### Concurrencia y frontera exacta

Cancelación y commitment utilizarán el mismo lock de la fila `CustomerOrder`.

La comparación normativa será:

```text
decision_at < production_commit_at
=> antes de la frontera

decision_at >= production_commit_at
=> después de la frontera
```

`decision_at` procederá del reloj autoritativo de la base de datos después de adquirir el lock, no del cliente ni de una hora congelada antes de esperar.

El protocolo deberá cubrir cancelación confirmada antes, commitment confirmado primero, solicitudes concurrentes alrededor del cutoff, scheduler atrasado, retry idempotente, timezone de sucursal con persistencia UTC y un milestone ya materializado que nunca se revierte por cambios de reloj.

No habrá lock global de pedidos.

### Liberación de reservas en cancelación

#### `PENDING`

Normalmente:

```text
reservation=0
release=0
```

porque la reserva nace en `READY`.

#### `READY`

Al cancelar:

```text
release remaining reservation exactly once
```

Efecto:

```text
on_hand no cambia
reserved disminuye
available aumenta
```

#### `DELIVERED`

No se cancela. Una devolución posterior utiliza DEC-09.

### `EXPIRED` y `NO_SHOW`

Serán transiciones terminales explícitas y auditables.

No bastará:

```text
now > pickup_time
```

para modificar automáticamente el pedido.

Cada transición identificará:

```text
reason
actor o system actor autorizado
policy snapshot
transition timestamp
PRODUCTION_COMMITTED evidence
financial resolution reference
reservation release
```

DEC-10 no fija grace period, horas ni días. El tratamiento financiero utilizará `PRODUCTION_COMMITTED` y la política snapshot aplicable, y no reconocerá ingreso ni ejecutará una transición por el mero paso del tiempo sin evento o comando durable.

### Sucursal de fulfillment

Cada pedido tendrá una única:

```text
fulfillment_branch_id
```

Será inmutable después de la confirmación.

Dentro de esa sucursal ocurrirán ordinariamente:

```text
READY
reservation
production/fulfillment
DELIVERED
advance
settlement
refund
```

Los distintos pagos podrán pertenecer a diferentes `CashSession` o turnos de la misma sucursal.

No se habilitarán:

```text
cross-branch fulfillment implícito
cross-branch payment implícito
```

El acceso `GLOBAL` de DEC-04 no autoriza mover silenciosamente el fulfillment.

### Pagos y caja

Cada movimiento financiero del pedido identificará, según corresponda:

```text
order_id
financial type
amount
fulfillment branch
cash_session_id
workstation
actor
timestamp
idempotency reference
```

Un anticipo, liquidación o refund pertenecerá al turno donde físicamente se mueva el dinero y participará en el cierre de esa `CashSession` conforme a DEC-06.

No todos los pagos del pedido deberán pertenecer al mismo turno.

### Relación con DEC-06

Todo `ADVANCE`, `SETTLEMENT` o `REFUND` que afecte caja deberá:

- adquirir la frontera de `CashSession`;
- validar el estado aplicable;
- crear el movimiento financiero canónico;
- participar en cash close;
- quedar incluido en expected y blockers.

No se reabrirán cajas cerradas.

### Relación con DEC-07

Como mínimo, operaciones equivalentes a las siguientes serán idempotentes:

```text
order.create
order.advance
order.amend
order.production_commit
order.mark_ready
order.deliver
order.cancel
order.expire
order.no_show
order.refund
```

Un replay `COMPLETED` no duplicará:

```text
payment
reservation
reservation consumption
revenue recognition
refund
audit
outbox
```

### Relación con DEC-08

Se preservarán estas reglas:

```text
READY -> full exact-product reservation
CANCELED/EXPIRED -> release remaining reservation
DELIVERED -> consume reservation exactly once
```

Los pedidos no usarán reservas de clase.

La reserva no disminuirá `on_hand`. La entrega disminuirá `on_hand` y `reserved` exactamente una vez.

### Relación con DEC-09

Una vez que el pedido alcance `DELIVERED`, no se cancelará para corregir una entrega.

Una devolución o corrección posterior utilizará DEC-09. No se editará el pedido histórico para simular una devolución.

### Dependencias posteriores

#### DEC-11

- pago mixto;
- cambio;
- distribución de anticipos o saldos por medio;
- refund por medio.

#### DEC-12

- producción planeada;
- reconstrucción o conciliación;
- inicio físico observado;
- eventos manuales, inferencias, sensores, telemetría y Living Lab.

`production_started` podrá existir como dato operativo o experimental de DEC-12, pero no será la frontera comercial de cancelación de DEC-10.

```text
dato experimental
!=
autoridad financiera
```

#### DEC-13

- pricing;
- promociones;
- descuentos;
- cálculo inicial del snapshot.

#### DEC-14

- pagos y refunds externos;
- `PROCESSING`;
- `UNKNOWN`;
- reconciliación.

#### DEC-19

- pedidos y pagos históricos;
- clasificación financiera;
- reservas históricas inexistentes;
- evidencia histórica de producción.

Estas decisiones no se resuelven mediante DEC-10.

### Modelo conceptual mínimo

Sin imponer nombres físicos, el modelo deberá ser equivalente a:

```text
CustomerOrder
  fulfillment_branch_id
  status
  current_version
  total_snapshot
  net_paid_amount
  minimum_advance_policy/version
  cancellation_policy/version
  production_commit_at
  production_commit_policy_version
  production_commit_timezone
  production_commit_intent_id
  production_commitment_recorded_at nullable
  delivered/canceled terminal metadata
```

```text
CustomerOrderVersion
  order_id
  version_number
  commercial snapshot
  production_commit_at
  policy/calculation snapshot
  timezone/offset snapshot
```

Evento durable equivalente:

```text
order.production_committed
```

La forma física podrá variar si conserva las mismas invariantes, la identidad causal y la separación entre `effective_at` y `recorded_at`.

```text
CustomerOrderVersionItem
  product_id
  quantity
  unit_price_snapshot
  line_total_snapshot
```

```text
CustomerOrderFinancialEntry
  type
  amount
  cash context
  causal/idempotency reference
```

La implementación evolucionará `CustomerOrderPayment` hacia el subledger canónico y no mantendrá dos libros financieros permanentes en paralelo.

### Locking y concurrencia

Orden conceptual:

```text
1. IdempotencyRecord
2. CustomerOrder/current version
3. CashSession cuando aplique
4. InventoryBalance/Reservation según DEC-08
5. otros recursos
6. efectos/audit/outbox
7. commit
```

Para creación:

```text
IdempotencyRecord
-> CashSession
-> insertar agregado
```

Resultados normativos:

```text
no_global_order_lock=true
different_orders_can_progress_concurrently=true
different_branches_can_progress_concurrently=true
overpayment_race_safe=true
state_transition_race_safe=true
reservation_race_safe=true
production_commitment_race_safe=true
```

Cancelación, amendment, commitment y `READY` compartirán el lock de la fila `CustomerOrder`. El scheduler y la materialización oportunista reutilizarán la misma identidad estable del commitment.

### Rendimiento

La dirección técnica será:

- `net_paid_amount` materializado o una proyección equivalente para lectura rápida;
- subledger causal como respaldo;
- índices por pedido, status, sucursal y pagos;
- ausencia de full payment scans innecesarios;
- ausencia de full inventory ledger scans;
- ausencia de locks globales;
- ausencia de integraciones externas bajo locks de inventario.

DEC-10 no fija un SLA numérico sin baseline.

### Errores conceptuales

Códigos estables equivalentes:

```text
ORDER_ADVANCE_MINIMUM_REQUIRED
ORDER_OVERPAYMENT_NOT_ALLOWED
ORDER_INVALID_TRANSITION
ORDER_READY_STOCK_INSUFFICIENT
ORDER_PARTIAL_RESERVATION_NOT_ALLOWED
ORDER_NOT_FULLY_PAID
ORDER_PARTIAL_DELIVERY_NOT_SUPPORTED
ORDER_ITEMS_LOCKED_AFTER_READY
ORDER_PRODUCTION_ALREADY_COMMITTED
ORDER_CANCELLATION_WINDOW_CLOSED
ORDER_PRODUCTION_COMMITMENT_CONFLICT
ORDER_PRODUCTION_COMMIT_AT_INVALID
ORDER_AMENDMENT_AFTER_PRODUCTION_COMMITMENT
ORDER_PRODUCTION_COMMITMENT_ALREADY_RECORDED
ORDER_ALREADY_DELIVERED
ORDER_CANCELLATION_NOT_ALLOWED
ORDER_BRANCH_MISMATCH
```

Semántica general recomendada:

```text
409 = conflicto con estado, recurso o concurrencia
422 = payload o regla semántica de entrada inválida
403 = autorización o scope cuando corresponda
```

### Auditoría y outbox

Eventos conceptuales equivalentes:

```text
order.created
order.payment_received
order.amended
order.production_committed
order.ready
order.delivered
order.canceled
order.expired
order.no_show
order.refunded
order.revenue_recognized
```

Cada evento auditará como mínimo, cuando corresponda:

```text
order_id
version
actor
fulfillment_branch_id
cash_session_id
old/new status
total
minimum advance
net_paid
payment/refund
production_commit_at
commitment effective_at/recorded_at
commitment policy/version
cancellation responsibility
reason
inventory reservation reference
request_id
idempotency reference no secreta
timestamp
```

Como mínimo serán idempotentes:

```text
order.production_commit
order.cancel
order.amend
order.mark_ready
```

Milestone, marker del pedido, cancelación/refund cuando aplique, release de reserva, auditoría, outbox e idempotencia compartirán la transacción correspondiente. Un replay no duplicará milestone, refund, release, auditoría ni outbox.

### Migración conceptual

La implementación posterior deberá:

1. ampliar la máquina de estados con `EXPIRED` y `NO_SHOW`;
2. implementar en backend el mínimo del 50 %;
3. persistir snapshots y versiones de políticas;
4. conservar `product_id` exacto;
5. evolucionar `CustomerOrderPayment` al subledger financiero canónico;
6. materializar `net_paid`;
7. proteger el sobrepago concurrente;
8. integrar reservas completas en `READY`;
9. consumir reservas en `DELIVERED`;
10. crear reconocimiento de ingreso exactly-once;
11. sustituir normativamente `production_started` por `PRODUCTION_COMMITTED`;
12. añadir `production_commit_at` y su policy snapshot;
13. añadir la identidad estable y el marker durable del commitment;
14. añadir el evento `order.production_committed`;
15. implementar scheduler/worker y fallback de materialización oportunista;
16. añadir locking del agregado para cancelación, commitment, amendment y `READY`;
17. añadir `cancellation_responsibility` y aplicar las reglas CUSTOMER/MERCHANT;
18. eliminar la regla temporal vigente de un día antes de `requested_for_at`;
19. introducir historial versionado de amendments y cutoff;
20. crear refunds causales;
21. incorporar comandos `EXPIRED` y `NO_SHOW`;
22. integrar DEC-07;
23. completar auditoría, outbox e idempotencia causal;
24. exponer cutoff y commitment en los contratos;
25. actualizar OpenAPI backend-first;
26. regenerar el cliente TypeScript;
27. actualizar POS y Backoffice;
28. reconciliar históricos mediante DEC-19.

No se inventarán pagos, reservas, estados productivos, responsabilidades ni `production_started` históricos.

### Pruebas futuras obligatorias

#### Creación

- exactamente 50 %;
- más de 50 %;
- menos de 50 % rechazado;
- redondeo;
- sobrepago;
- replay;
- `CashMovement` y cash close.

#### Productos

- producto exacto;
- clase sólo como navegación;
- línea genérica rechazada.

#### Pagos

- múltiples anticipos;
- pago final;
- diferentes turnos;
- sobrepago concurrente.

#### `READY`

- reserva completa;
- stock insuficiente;
- cero reserva parcial;
- concurrencia;
- replay;
- transición anterior al cutoff rechazada o diferida;
- transición posterior al commitment sin modificar retrospectivamente la frontera.

#### `DELIVERED`

- pedido completamente pagado;
- saldo pendiente rechazado;
- consumo exactly-once;
- revenue exactly-once;
- entrega parcial rechazada.

#### Cancelación

- cliente antes de `production_commit_at`: refund 100 %;
- cliente exactamente en `production_commit_at`: refund 0;
- cliente después de `production_commit_at`: refund 0;
- responsabilidad `MERCHANT`: refund 100 % antes o después del commitment;
- scheduler puntual;
- scheduler retrasado sin extensión de ventana;
- materialización oportunista;
- cancelación frente a commitment concurrentes;
- timezone y DST;
- cambio posterior de timezone sin alterar históricos;
- liberación de reserva en `READY`;
- `PENDING` sin reserva;
- `DELIVERED` no cancelable.

#### Amendments

- aumento del total;
- incumplimiento posterior del 50 %;
- disminución que causaría sobrepago;
- amendment anterior al commitment con cutoff versionado;
- cutoff retroactivo rechazado;
- amendment posterior a `PRODUCTION_COMMITTED` rechazado;
- amendment después de `READY` rechazado.

#### `PRODUCTION_COMMITTED`

- evento durable exactamente una vez;
- `effective_at` y `recorded_at` distintos cuando el scheduler se retrase;
- mismo resultado con scheduler, comando interno o materialización oportunista;
- retry exactly-once;
- milestone, auditoría y outbox exactly-once;
- ausencia de lock global.

#### `EXPIRED` y `NO_SHOW`

- transición explícita;
- ausencia de transición automática sólo por reloj;
- resolución financiera;
- release de reserva.

#### Atomicidad y concurrencia

- payment vs payment;
- `READY` vs cancelación;
- delivery vs cancelación;
- reserva vs venta competidora;
- crash;
- respuesta perdida;
- payment, refund, reservation, revenue, audit y outbox exactly-once.

### Evidencia técnica asociada

En el código vigente:

- los estados de pedido son sólo `PENDING`, `READY`, `DELIVERED` y `CANCELED`;
- `CustomerOrderItem.product_id` ya es obligatorio;
- se conservan precios y totales, pero no versiones completas de políticas;
- se permiten anticipos inferiores al 50 %;
- no existe un comando general de pagos posteriores;
- `CustomerOrderPayment` contiene `ADVANCE`, `SETTLEMENT` y `REFUND`;
- esos pagos no crean el `CashMovement` canónico consumido por cash close;
- no existe protección transversal race-safe contra sobrepago;
- `READY` no reserva inventario;
- `DELIVERED` no consume reservas;
- no existe reconocimiento de ingreso de pedido;
- la cancelación usa actualmente `requested_for_at - 1 día` como regla temporal;
- no existen `production_commit_at`, policy snapshot ni milestone durable;
- no existe scheduler de pedidos; el worker actual sólo consulta el outbox;
- `ProductionBatch.started_at` no está ligado al pedido y requiere una acción Backoffice no garantizada;
- no existen amendments versionados;
- no existen `EXPIRED` ni `NO_SHOW`;
- no existe idempotencia transversal conforme a DEC-07;
- no existe locking adecuado del agregado.

Estos hechos no equivalen a implementación de DEC-10.

### Consecuencias, límite e historial

- **Tareas afectadas:** `ZM-FIN-003`, `ZM-FIN-008` y las tareas posteriores del Plan Maestro que implementen pedidos, caja, inventario, producción, contratos, clientes, reportes y migración de datos.
- **Consecuencias:** subledger financiero de pedidos, snapshots versionados, enforcement backend del 50 %, reserva completa, reconocimiento de ingreso al entregar, cutoff `production_commit_at`, milestone `PRODUCTION_COMMITTED`, cancelación CUSTOMER/MERCHANT, locking por pedido, idempotencia, auditoría, outbox y pruebas de concurrencia y rendimiento.
- **Dependencias:** DEC-06 para caja y cierre; DEC-07 para idempotencia; DEC-08 para reservas e inventario; DEC-09 para devoluciones posteriores; DEC-11 para medios mixtos; DEC-12 para datos productivos sin autoridad sobre el refund; DEC-13 para pricing; DEC-14 para pagos externos; DEC-19 para históricos.
- **Límite:** DEC-10 define la política y el modelo conceptual; no certifica que pedidos, pagos, reservas, reconocimiento de ingreso, cancelaciones, expiración, locking, idempotencia, migraciones, contratos, clientes o pruebas estén implementados.
- **Historial:** `PENDIENTE` desde 2026-08-26; versión inicial `APROBADA` por el propietario el 2026-08-28 con `production_started` como frontera; evidencia operativa posterior del mismo día demostró que esa señal no podía garantizarse sin captura rutinaria o sensores; revisión vigente del 2026-08-28 sustituye exclusivamente esa frontera por `PRODUCTION_COMMITTED`; las demás reglas aprobadas permanecen sin cambio.

## DEC-11 — Pago mixto

- **Estado:** `APROBADA`
- **Fecha:** 2026-08-28
- **Propietario:** propietario de ZeroMerma
- **Contenido aprobado:** clasificación derivada `MIXED`, composición financiera por legs reales, cambio sólo en efectivo, refunds `CASH_FIRST`, capacidad de caja, liquidación parcial, moneda única, idempotencia, locking, reportes y migración.
- **Respuesta aprobada:** política normativa, modelos conceptuales, invariantes, dependencias y pruebas futuras descritos en esta decisión.

### `MIXED` es una clasificación derivada

`MIXED` será una clasificación derivada de la composición real de una transacción. No será un medio financiero persistido.

Ejemplo normativo:

```text
Payment:
  CASH applied=400
  CARD applied=600

classification=MIXED
```

La fuente financiera real será:

```text
CASH=400
CARD=600
```

No se persistirá ni contabilizará:

```text
MIXED=1000
```

La derivación será equivalente a:

```text
methods =
  distinct method_code
  de legs aplicados > 0

0 methods -> NONE
1 method  -> ese método
>=2       -> MIXED
```

Dos o más legs del mismo método no producirán clasificación `MIXED`. La regla será general para dos o más métodos distintos, aunque la UI exponga inicialmente sólo los métodos habilitados.

Se distinguirá entre:

```text
classification de una transacción
```

y:

```text
composición histórica total de un pedido
```

La composición histórica total será una dimensión analítica derivada, no un medio de pago.

### Conservación del importe del cobro

Para un cobro completo deberá cumplirse:

```text
sum(PaymentLeg.applied_amount)
=
Payment.amount_due
```

No se permitirá:

```text
sum(applied) < amount_due
sum(applied) > amount_due
```

Cuando corresponda, se distinguirán conceptualmente:

```text
tendered_amount
applied_amount
change_amount
```

El importe presentado por el cliente no sustituirá al importe efectivamente aplicado al documento.

### Cambio exclusivamente en efectivo

Sólo `CASH` podrá generar cambio.

Ejemplo normativo:

```text
amount_due=100

CARD:
  applied=60

CASH:
  applied=40
  tendered=50
  change=10
```

La composición financiera será:

```text
CARD=60
CASH=40
```

El efecto neto de caja será:

```text
CashMovement IN 40
```

Reglas:

- para `CASH`, `tendered >= applied`;
- para `CASH`, `change = tendered - applied`;
- para un medio no `CASH`, `change = 0`;
- un medio no efectivo nunca generará cambio en efectivo;
- el efecto financiero `CASH` se producirá una única vez por `applied_amount` neto.

La representación canónica conservará `tendered`, `applied` y `change` en el leg. No se creará una segunda salida de caja por el cambio que duplique el efecto económico ya expresado por el importe neto aplicado.

### Modelo conceptual de `Payment`

Se utilizará un modelo conceptual equivalente a:

```text
Payment
  id
  source_document_type
  source_document_id
  operation_code
  amount_due
  amount_settled
  currency_code
  status
  idempotency_record_id
  created_at
  completed_at nullable
```

```text
PaymentLeg
  id
  payment_id
  sequence
  method_code
  applied_amount
  tendered_amount nullable
  change_amount
  currency_code
  status
  cash_session_id nullable
  original_tender_reference nullable
  external_operation_reference nullable
  causal_effect_code
  created_at
  completed_at nullable
```

Invariantes conceptuales:

```text
method_code != MIXED
applied_amount > 0
change_amount >= 0
leg.currency == payment.currency
```

Para `CASH`:

```text
cash_session_id requerido
tendered_amount requerido
tendered = applied + change
```

Para un método no `CASH`:

```text
change=0
```

Los nombres físicos podrán adaptarse durante implementación, pero no podrán alterar estas invariantes.

### Origen causal obligatorio del refund

Todo refund deberá tener un origen causal válido.

Para devoluciones de ventas:

```text
SaleReturn validada conforme DEC-09
-> Refund
```

Será suficiente cualquiera de estas evidencias cuando permita localizar y validar inequívocamente la operación:

- ticket físico válido;
- venta o ticket localizado en el sistema.

No será obligatorio presentar papel cuando la venta pueda localizarse y validarse electrónicamente. No se permitirá un refund `CASH` arbitrario sin una venta, devolución o documento causal válido.

Para pedidos, DEC-10 determinará el derecho y el importe reembolsable; DEC-11 materializará la composición financiera.

### Refund no limitado al medio original

La composición real de un refund no quedará limitada por la composición del pago original.

Ejemplo normativo:

```text
venta original:
CASH=40
CARD=60

refund válido=80
cash_capacity>=80
```

Resultado permitido:

```text
refund:
CASH=80
```

El refund podrá entregar 80 en efectivo aunque originalmente sólo hubieran entrado 40 en `CASH`.

Siempre se preservarán:

```text
original payment composition
actual refund composition
causal relationship
```

No se exigirá revertir `CARD` únicamente porque la venta original utilizó `CARD`.

### Prioridad `CASH_FIRST`

La política ordinaria será:

```text
refund_priority = CASH_FIRST
```

El algoritmo conceptual será:

```text
cash_capacity =
  capacidad autoritativa de la CashSession abierta

cash_refund =
  min(refund_due, cash_capacity)

remaining =
  refund_due - cash_refund
```

DEC-11 no introducirá:

- reparto proporcional;
- prioridad proporcional basada en los medios originales;
- fondo mínimo arbitrario;
- `safety reserve` no aprobado.

La política no exige que un refund sea proporcional a la composición original.

Ejemplo de reparto no normativo y no obligatorio:

```text
original:
40 CASH
60 CARD

refund=50

20 CASH
30 CARD
```

La política aprobada será:

```text
CASH first
then remaining eligible non-cash
```

### Capacidad autoritativa de efectivo

La capacidad de backend será equivalente a:

```text
expected_cash =
    opening_amount
  + committed CASH inflows
  - committed CASH outflows

cash_capacity = max(expected_cash, 0)
```

Incluirá, cuando los conceptos correspondientes estén implementados:

- apertura;
- ventas `CASH` netas del cambio;
- anticipos de pedidos;
- liquidaciones;
- refunds anteriores;
- pagos operativos;
- depósitos y retiros;
- los demás `CashMovement` confirmados.

Regla obligatoria:

```text
ordinary refund
must not produce
authoritative expected_cash < 0
```

No se fijará un fondo mínimo adicional. El sistema puede desconocer las denominaciones físicas exactas durante el turno; esa limitación no cambia la capacidad contable autoritativa.

Una discrepancia física se resolverá operativamente y mediante cierre o conciliación conforme a DEC-06. No se inventará capacidad de efectivo para ocultarla.

### Efectivo insuficiente y liquidación parcial

Si:

```text
refund_due > cash_capacity
```

se aplicará:

```text
CASH = cash_capacity
remaining = refund_due - cash_capacity
```

Ejemplo:

```text
refund_due=500
cash_capacity=300

CASH completed=300
remaining=200
```

El remanente se intentará únicamente mediante medios no efectivos originales elegibles. Nunca se permitirá:

```text
cash refund > cash_capacity
expected_cash < 0
```

Caso obligatorio para una venta pagada sólo en efectivo:

```text
original payment=CASH
refund_due=100
cash_capacity=40
```

Resultado:

```text
settled=40
pending=60
status=PARTIALLY_SETTLED
```

o una representación técnicamente equivalente.

No se permitirá:

```text
cash=-60
invented CARD
refund fully settled
```

El derecho financiero pendiente permanecerá explícito hasta su resolución.

### Remanente no efectivo

Después de agotar la capacidad `CASH`:

- sólo podrán utilizarse métodos no efectivos originales elegibles;
- se conservarán las referencias de las operaciones originales;
- no se superará lo causalmente reembolsable por cada operación externa;
- no se inventará un método nuevo.

La prioridad exacta entre varios procesadores externos pertenece a DEC-14.

Si un remanente externo queda `PENDING`, `PROCESSING` o `UNKNOWN`, conforme al modelo externo definitivo:

- no se considerará liquidado;
- no se sustituirá silenciosamente por más `CASH` cuando no exista capacidad;
- no se repetirá ciegamente;
- conservará su identidad externa;
- el refund agregado no se considerará completamente resuelto.

DEC-14 definirá autorización, refund, void, reconciliación y estados externos.

### Modelo conceptual de `Refund`

Se utilizará un agregado equivalente a:

```text
Refund
  id
  source_return_id/source_document
  amount_due
  amount_settled
  amount_pending
  status
  idempotency_record_id
```

y legs equivalentes a:

```text
RefundLeg
  id
  refund_id
  method_code
  amount
  original_tender_reference nullable
  cash_session_id nullable
  external_operation_reference nullable
  status
  causal_effect_code
```

El modelo deberá representar, por ejemplo:

```text
refund due=500

CASH=300 COMPLETED
CARD=200 PROCESSING
```

sin duplicar la devolución física o documental.

Los estados conceptuales deberán distinguir como mínimo:

```text
PENDING
PARTIALLY_SETTLED
PROCESSING
UNKNOWN
COMPLETED
REJECTED
```

Invariante terminal:

```text
refund COMPLETED
iff
amount_settled == amount_due
and
no required leg remains non-terminal
```

Cuando exista remanente:

```text
amount_settled + amount_pending
=
amount_due
```

El fallo o la incertidumbre de un leg externo no eliminará silenciosamente la obligación financiera.

### Redondeo y moneda

Todos los importes utilizarán:

```text
Decimal/Numeric
scale=0.01
ROUND_HALF_UP
```

No se requiere una regla de centavo residual proporcional porque DEC-11 no impone reparto proporcional.

Cuando el refund esté completamente resuelto:

```text
sum(refund legs)
=
refund_due
```

Cada documento tendrá una sola moneda y deberá cumplirse:

```text
all legs currency == document currency
```

DEC-11 no soportará:

```text
mixed-currency payment
FX conversion inside payment
FX gain/loss
```

Un soporte multi-divisa futuro requerirá una decisión explícita.

### Caja y cierre

Cada leg `CASH`:

- pertenecerá a una `CashSession`;
- adquirirá la frontera transaccional de DEC-06;
- producirá el `CashMovement` causal correspondiente;
- participará en `expected_cash` y en el cierre.

Cada leg no efectivo participará en su conciliación real.

Ejemplo:

```text
payment:
CASH +400
CARD +600

refund:
CASH -100
```

Resultado:

```text
cash net effect=+300
card component=+600
```

No se reducirá `CARD` porque el refund real haya sido `CASH`.

`MIXED` se retirará conceptualmente como método de conteo o ledger financiero. Un refund `PENDING`, `PROCESSING` o `UNKNOWN` que todavía pueda alterar el turno podrá bloquear el cierre conforme a DEC-06. Una caja cerrada no se reabrirá para ejecutar un refund posterior.

### Reportes sin doble conteo

Los contratos analíticos separarán:

```text
transaction_classification
actual_method
```

Deberá ser posible reportar:

```text
mixed_transaction_count
cash_collected
card_collected
cash_refunded
card_refunded
```

Los importes se agregarán desde los legs reales. `MIXED` servirá únicamente como dimensión de clasificación.

Nunca se sumarán simultáneamente:

```text
MIXED total
+
CASH legs
+
CARD legs
```

como volumen financiero.

### Aplicación a pedidos conforme a DEC-10

El mismo modelo de payment legs aplicará a:

```text
minimum 50% advance
additional advance
settlement
refund
```

Ejemplo:

```text
order total=1000
minimum advance=500

CASH applied=200
CARD applied=300

net_paid=500
classification=MIXED
```

El mínimo del 50 % se evaluará sobre:

```text
sum(applied amounts)
```

No se evaluará sobre el efectivo presentado antes de calcular cambio.

Cada transacción financiera del pedido conservará su propia composición. DEC-10 seguirá determinando `amount_due`, anticipo mínimo, saldo y derecho de refund por cancelación; DEC-11 sólo materializará los medios.

### Idempotencia del agregado y sus legs

Conforme a DEC-07 existirá una intención agregada para operaciones equivalentes a:

```text
sale.payment
order.advance
order.settlement
return.refund
```

y causalidad exactamente una vez por leg.

Defensas conceptuales:

```text
IdempotencyRecord UNIQUE(idempotency_key)

PaymentLeg UNIQUE(payment_id, causal_effect_code)

RefundLeg UNIQUE(refund_id, causal_effect_code)

CashMovement UNIQUE(source/effect causal identity)
```

Un replay no podrá producir:

```text
duplicate CASH leg
duplicate CARD leg
duplicate change
duplicate CashMovement
duplicate refund leg
duplicate audit/outbox effect
```

Un retry de un refund parcialmente liquidado:

- recuperará el mismo agregado;
- no volverá a ejecutar el leg `CASH` ya liquidado;
- no generará otro `CashMovement`;
- no creará otra identidad externa;
- devolverá el estado agregado vigente.

`X-Request-ID` continuará siendo únicamente trazabilidad.

### Relación con decisiones aprobadas y posteriores

- **DEC-06:** preserva `CashSession` abierta para legs `CASH`, la frontera transaccional, `expected_cash` y los blockers financieros. No se reabrirán cajas cerradas.
- **DEC-07:** `Payment`, `Refund` y sus legs serán exactly-once; DEC-11 no reinterpreta la política transversal de idempotencia.
- **DEC-09:** determina validez, cantidad retornable, disposición física e inmutabilidad de la devolución. DEC-11 determina únicamente la composición financiera del refund.
- **DEC-10:** determina `amount_due`, anticipo mínimo, saldo y derecho de refund por cancelación. DEC-11 materializa los medios sin alterar esa política.
- **DEC-14:** definirá autorización, capture, refund, void, `PROCESSING`, `UNKNOWN`, reconciliación y asignación entre procesadores externos.

Cambiar el medio financiero de un refund no cambiará la realidad física de la devolución.

DEC-11 fija respecto de operaciones externas:

```text
no blind retry
no fake terminal success
no silent CASH beyond capacity
```

### Locking y concurrencia

El orden conceptual será:

```text
1. IdempotencyRecord
2. business document / Refund / CustomerOrder
3. CashSession cuando CASH aplique
4. metadata/intent externo cuando corresponda
5. legs / CashMovement / efectos
6. audit/outbox
7. commit
```

No habrá lock global de pagos.

Resultados normativos:

```text
no_global_payment_lock=true
different_cash_sessions_can_progress_concurrently=true
cash_refund_capacity_race_safe=true
refund_amount_race_safe=true
```

Caso obligatorio de concurrencia:

```text
cash_capacity=100

refund A=80
refund B=80
```

Los dos refunds sólo podrán liquidar conjuntamente 100 en efectivo. La capacidad se comprobará bajo la frontera de la `CashSession`, de modo que ninguna carrera produzca `expected_cash` negativo.

### Rendimiento

La implementación deberá mantener:

- proyección o materialización rápida del efectivo esperado;
- ledger causal como respaldo;
- índices por payment, refund, método, estado y documento origen;
- fast-path de replay;
- ausencia de escaneo completo del historial de pagos por operación;
- ausencia de escaneo completo innecesario del historial de refunds;
- ausencia de lock global;
- ausencia de llamadas externas bajo locks largos;
- reportes desde legs o proyecciones indexadas.

No se fijará un SLA sin una línea base medible.

### Errores conceptuales

Se registran códigos estables equivalentes a:

```text
PAYMENT_TENDER_SUM_MISMATCH
PAYMENT_CHANGE_ONLY_CASH
PAYMENT_OVERPAYMENT_NOT_ALLOWED
PAYMENT_MIXED_CURRENCY_NOT_ALLOWED

REFUND_SOURCE_REQUIRED
REFUND_AMOUNT_INVALID
REFUND_CASH_CAPACITY_INSUFFICIENT
REFUND_PARTIALLY_SETTLED
REFUND_EXTERNAL_PENDING
REFUND_ALREADY_SETTLED
```

`REFUND_CASH_CAPACITY_INSUFFICIENT` no implicará normalmente el rechazo total de un refund ordinario `CASH_FIRST`; activará liquidación parcial y conservación explícita del remanente pendiente.

Los contratos HTTP definitivos se establecerán backend-first durante la implementación.

### Auditoría y outbox

Se contemplan eventos conceptuales equivalentes a:

```text
payment.committed
payment.leg.committed
refund.committed
refund.partially_settled
refund.leg.settled
refund.pending
refund.external_processing
refund.external_unknown
```

La evidencia auditable incluirá, según corresponda:

```text
source document
payment/refund id
original payment composition
actual refund composition
method
applied
tendered
change
cash_session
external reference no secreta
actor
request_id
idempotency reference no secreta
timestamp
```

No se registrarán secretos. Un replay no duplicará eventos de negocio.

### Migración conceptual

La estrategia será:

1. Inventariar dónde `MIXED` está persistido actualmente.
2. Crear aggregates y legs canónicos de pago.
3. Crear `Refund` y `RefundLeg`.
4. Migrar `SalePayment` a legs.
5. Migrar pagos de pedidos.
6. Migrar devoluciones actuales.
7. Eliminar `MIXED` como método financiero para operaciones nuevas.
8. Conservar `MIXED` sólo como clasificación derivada.
9. Separar `tendered`, `applied` y `change`.
10. Añadir causalidad e idempotencia a `CashMovement`.
11. Implementar `CASH_FIRST`.
12. Implementar refund parcial y pendiente.
13. Introducir una proyección autoritativa de capacidad de caja.
14. Adaptar cash close.
15. Adaptar reportes.
16. Adaptar ventas.
17. Adaptar pedidos.
18. Adaptar devoluciones.
19. Coordinar estados externos con DEC-14.
20. Actualizar OpenAPI backend-first.
21. Regenerar el cliente TypeScript.
22. Actualizar POS y Backoffice.
23. Retirar las estructuras financieras anteriores después del cutover.
24. Tratar históricos ambiguos conforme a DEC-19.

No se inferirán composiciones históricas `MIXED` sin evidencia.

### Pruebas futuras obligatorias

La implementación deberá cubrir como mínimo:

#### Payment

- `CASH`;
- `CARD`;
- `CASH` más `CARD`;
- tres o más métodos;
- dos legs del mismo método;
- suma aplicada distinta del due;
- sobrepago;
- cambio `CASH`;
- cambio en método no efectivo rechazado;
- moneda diferente rechazada;
- replay.

#### Cash close y reportes

- split real por legs;
- clasificación derivada;
- ausencia de doble conteo;
- efectivo neto después del cambio.

#### Pedidos

- anticipo mixto del 50 %;
- anticipos posteriores;
- settlement;
- rechazo de sobrepago;
- cambio `CASH`.

#### Refund

- venta `CARD` con refund total `CASH`;
- refund `CASH` superior al `CASH` original;
- prioridad `CASH_FIRST`;
- capacidad insuficiente con remanente externo;
- venta sólo `CASH` con capacidad insuficiente y estado parcial o pendiente;
- dos refunds concurrentes por capacidad;
- ticket electrónico válido sin papel;
- fuente inválida;
- retry exactly-once.

#### Operación externa

- `PROCESSING`;
- `UNKNOWN`;
- ausencia de blind retry;
- misma identidad durante reconciliación.

#### Moneda

- una sola moneda aceptada;
- mixed currency rechazada.

Estas pruebas no se ejecutan ni implementan mediante esta decisión documental.

### Evidencia técnica asociada

En el código vigente:

- las ventas ya persisten legs reales y rechazan `MIXED` como leg;
- otros modelos todavía permiten `MIXED`;
- las ventas validan la suma exacta;
- existen `tendered` y `change`;
- el movimiento de caja actual usa el `applied CASH` neto;
- el pago mixto POS está fijado a `CASH` y `CARD`;
- POS impide actualmente algunos escenarios de cambio mixto;
- los pedidos permiten `CASH`, `CARD` y `MIXED`, y no crean el `CashMovement` canónico;
- los refunds de venta son sólo `CASH`;
- los refunds de pedido replican la composición original;
- no existe enforcement de capacidad de caja;
- no existe refund parcial o pendiente;
- no existen estados externos;
- algunas rutas de reporte todavía tratan `MIXED` como bucket directo;
- no existe idempotencia transversal conforme a DEC-07;
- no existe locking adecuado.

Estos hechos describen la implementación vigente y no equivalen a implementación de DEC-11.

### Consecuencias, límite e historial

- **Tareas afectadas:** `ZM-FIN-003`, `ZM-FIN-008` y las tareas posteriores del Plan Maestro que implementen pagos, pedidos, devoluciones, caja, reportes, contratos, clientes, migración de datos y medios externos.
- **Consecuencias:** aggregates y legs canónicos, `MIXED` derivado, cambio sólo `CASH`, capacidad autoritativa de caja, refunds `CASH_FIRST`, remanentes explícitos, reportes por legs, locking, idempotencia, auditoría y outbox.
- **Dependencias:** DEC-06 para `CashSession`, cash close y blockers; DEC-07 para idempotencia; DEC-09 para validez y causalidad de devolución; DEC-10 para pedidos y refund entitlement; DEC-14 para medios externos y reconciliación; DEC-19 para históricos ambiguos.
- **Límite:** DEC-11 define la política normativa y los modelos conceptuales; no certifica que pagos, refunds, capacidad de caja, estados externos, locking, idempotencia, migraciones, contratos, POS, Backoffice, reportes o pruebas estén implementados.
- **Historial:** `PENDIENTE` desde 2026-08-26; `APROBADA` por el propietario el 2026-08-28.

## DEC-12 — Producción

- **Estado:** `APROBADA`
- **Fecha:** 2026-08-28
- **Propietario:** propietario de ZeroMerma
- **Respuesta aprobada:** producción operativa de baja interacción, independiente de sensores, separada entre plan y corrida, con conciliación final mínima, reservas causales, WIP opcional, recetas versionadas, efectos físicos explícitos, asignaciones de output y una capa append-only de observaciones preparada para Living Lab.
- **Regla:** la realidad productiva canónica sólo nace de fuentes operativas autorizadas o de una conciliación/promoción explícita; una inferencia, observación o señal experimental no muta por sí sola el dominio.

### Principio operativo de baja interacción

1. Los panaderos no realizarán captura digital rutinaria.
2. Su interfaz ordinaria será un monitor de producción principalmente de sólo lectura.
3. No deberán llenar formularios, navegar pantallas ni registrar manualmente cada etapa.
4. ZeroMerma deberá funcionar completamente sin sensores, cámaras, básculas conectadas, RFID, NFC, voz ni hardware especializado.
5. No se pedirá al personal un dato que ZeroMerma pueda obtener de sus propios módulos o inferir razonablemente.
6. Cuando un dato físico real no pueda obtenerse de una fuente canónica, se resolverá mediante una conciliación final breve, precargada y realizada por un usuario autorizado, no necesariamente el panadero.
7. La captura humana normal será por excepción.
8. Un dato inferido no se presentará como realidad física confirmada.
9. La futura instrumentación no será requisito para operar el módulo.

Queda establecido:

```text
sensor_independent_core=true
routine_baker_data_entry=false
exception_based_capture=true
```

### Separación entre plan y corrida

El modelo conceptual mínimo será equivalente a:

```text
ProductionPlan
  DRAFT
  RELEASED
  CANCELLED

ProductionRun
  OPEN
  PENDING_RECONCILIATION
  COMPLETED
  CANCELLED
```

La forma física podrá variar durante la implementación si conserva las invariantes siguientes.

#### `ProductionPlan DRAFT`

- Es editable.
- No tiene efectos físicos.
- No está publicado como plan operativo definitivo.

#### `ProductionPlan RELEASED`

- Congela el snapshot de receta, cantidades, demanda y destinos.
- Es visible en el Production Board.
- Puede crear reservas de insumos.
- No afirma que la producción física comenzó.

#### `ProductionRun OPEN`

- Representa una corrida disponible para ejecución física.
- No implica `production_started`.
- No implica consumo, WIP ni output.

#### `PENDING_RECONCILIATION`

- La ejecución física pudo ocurrir.
- Falta confirmar o explicar output, consumo, retorno, merma o diferencias.
- Ningún valor inferido pendiente se considera realidad física canónica.

#### `COMPLETED`

- La conciliación final quedó confirmada.
- Movimientos físicos, reservas, output, retorno y merma son consistentes.
- Auditoría, outbox e idempotencia quedaron confirmados.

#### `CANCELLED`

- Es terminal.
- Si existieron efectos físicos, deben quedar reconciliados antes de confirmar la cancelación.

`IN_PROGRESS` no será una transición obligatoria del core. Podrá existir como observación, milestone opcional, dato manual confirmado o dato instrumental futuro, pero no se inventará cuando no exista evidencia.

### Planificación y Production Board

El Production Board será una superficie principalmente de sólo lectura para el personal de producción. Mostrará, como mínimo:

- productos;
- cantidades;
- prioridad;
- hora objetivo;
- pedidos relacionados claramente diferenciados;
- cantidades destinadas a pedidos;
- cantidades destinadas a stock;
- receta o versión aplicable cuando corresponda;
- faltantes o bloqueos;
- estado del plan.

No exigirá formularios rutinarios al panadero.

La planificación reutilizará la información ya existente en pedidos, ventas, inventario, recetas, sucursales, compras, horarios, transferencias y los demás módulos aplicables. No se volverá a pedir manualmente un dato ya disponible en ZeroMerma.

### Conciliación final mínima

Existirá una superficie separada equivalente a `Production Reconciliation / Supervisor`, utilizada por un usuario autorizado y precargada con:

- plan liberado;
- receta y versión;
- inputs teóricos;
- cantidades planeadas;
- demanda de pedidos;
- cantidad para stock;
- reservas;
- observaciones disponibles;
- output esperado;
- eventos automáticos disponibles.

El caso normal será:

```text
Confirmar sin diferencias
```

Esta acción deberá requerir una sola interacción.

La captura excepcional permitirá:

- corregir output real;
- corregir consumo;
- registrar retorno;
- registrar merma;
- registrar incidencia;
- registrar reproceso;
- explicar diferencias.

Una confirmación manual sin diferencias se clasificará como:

```text
source_kind=MANUAL
evidence_quality=CONFIRMED
```

No como:

```text
source_kind=SENSOR
evidence_quality=MEASURED
```

Si no existe fuente canónica ni conciliación:

```text
status=PENDING_RECONCILIATION
```

y los valores inferidos permanecerán no canónicos.

### Reserva de insumos al liberar

Al liberar un plan podrá crearse una reserva causal conforme a DEC-08:

```text
on_hand no cambia
reserved aumenta
available disminuye
```

La reserva deberá:

- corresponder al plan y sus líneas;
- ser idempotente;
- evitar doble disponibilidad;
- conservar producto, cantidad, ubicación, UOM y causalidad;
- liberarse, consumirse o reconciliarse exactamente una vez.

La mera publicación del plan no significa consumo físico.

### WIP opcional según evidencia

`WIP` no será obligatorio para operar la Capa 1.

Sólo una fuente operativa canónica podrá mover material:

```text
BACKROOM -> WIP
```

No podrán producir ese movimiento por sí solos:

- la llegada de una hora;
- la publicación del plan;
- una inferencia;
- una observación experimental;
- una señal no validada.

Si no existe evento canónico de emisión a WIP, la conciliación final podrá registrar atómicamente consumo real, retorno, merma, liberación de reserva no utilizada y output.

Si en el futuro existe instrumentación validada, podrá registrarse WIP antes de la conciliación.

Ambos modos utilizarán el mismo dominio, ledger, reservas, idempotencia, auditoría y modelo de conciliación. No se crearán dos arquitecturas paralelas.

### Receta versionada e inmutable

Cada plan y corrida referenciará una versión concreta de receta y conservará un snapshot equivalente a:

- receta y versión;
- ingredientes;
- cantidades;
- UOM;
- conversiones;
- output esperado;
- rendimiento esperado;
- datos de costo relevantes;
- timestamp de vigencia.

Reglas:

1. Una versión utilizada por un plan liberado o corrida no se editará.
2. Cambiar ingredientes, cantidades, UOM o rendimiento crea una nueva versión.
3. Desactivar una receta no modifica históricos.
4. Las cantidades planeadas quedan congeladas al liberar.
5. Los consumos y outputs reales no reescriben automáticamente la receta.
6. La receta representa expectativa; la conciliación representa realidad.

```text
recipe_expectation != production_actuals
```

### Consumo, retorno, merma y output

La conciliación deberá poder explicar:

```text
material emitido o reservado
=
consumo real
+ retorno
+ merma
+ remanente explícito autorizado
```

Reglas:

- el consumo teórico de receta no se considera consumo real sin confirmación;
- no se inventará consumo para cuadrar;
- no se ocultará merma dentro del consumo;
- el retorno será explícito;
- el remanente será explícito y justificado;
- el output real puede diferir del output planeado;
- no se creará output ficticio;
- UOM y causalidad serán obligatorias;
- los movimientos históricos serán inmutables;
- las correcciones usarán movimientos compensatorios;
- auditoría y outbox serán transaccionales;
- DEC-07 garantizará exactly-once.

### Merma explícita

Toda merma productiva canónica conservará como mínimo:

- plan/corrida;
- producto o insumo;
- cantidad;
- UOM;
- ubicación o contexto;
- razón;
- actor o fuente;
- `occurred_at`;
- `recorded_at`;
- referencia causal;
- referencia idempotente;
- movimiento hacia `WASTE` o disposición válida conforme a DEC-08/09.

No se usará una simple diferencia de rendimiento como sustituto de una merma canónica.

### Rendimiento

El rendimiento será una métrica derivada de datos canónicos. Como mínimo podrá comparar:

```text
output real / output esperado
```

y conservará:

- output esperado;
- output real;
- diferencia;
- porcentaje;
- receta/version;
- corrida;
- periodo.

El rendimiento será analítico; no modificará automáticamente la receta ni los movimientos, no inventará merma y no cambiará futuras producciones sin una decisión explícita.

### Output parcial

La arquitectura soportará output parcial cuando exista evidencia canónica, pero no será obligatorio capturarlo por tanda en la Capa 1.

Reglas:

- cada output parcial tendrá identidad causal única;
- será idempotente;
- afectará inventario exactamente una vez;
- conservará producto, cantidad, UOM, ubicación y timestamp;
- la conciliación final sumará outputs parciales;
- el cierre sólo registrará el delta no registrado previamente;
- se rechazará sobreconteo o duplicación.

La Capa 1 podrá operar únicamente con output final. Una futura Capa 2 podrá aportar outputs parciales medidos o promovidos.

### Corridas con varios pedidos y stock

El propietario aprobó expresamente:

> Una misma corrida de producción puede abastecer simultáneamente varios pedidos y producción para stock, siempre que existan asignaciones explícitas de cantidades por destino y no exista doble asignación.

Existirá una estructura equivalente a:

```text
ProductionDemandAllocation
  production_plan_id
  production_run_id nullable
  order_item_id nullable
  destination: ORDER | STOCK
  planned_quantity
  fulfilled_quantity
  causal identity
```

Reglas:

1. Cada asignación indicará un destino explícito.
2. Una asignación `ORDER` referenciará una línea de pedido concreta.
3. Una asignación `STOCK` identificará producto, sucursal y ubicación destino.
4. La suma planificada de asignaciones no excederá el output planeado.
5. La suma cumplida no excederá el output real conciliado.
6. No habrá doble asignación del mismo output.
7. Un output podrá distribuirse entre varios pedidos y stock.
8. Las cantidades no asignadas deberán quedar explícitamente como stock, remanente o diferencia pendiente; nunca desaparecerán.
9. Las asignaciones conservarán trazabilidad, auditoría e idempotencia.
10. La corrida no se dividirá artificialmente por pedido si una producción por lote satisface varios destinos.

Ejemplo normativo:

```text
Corrida:
40 conchas

Asignaciones:
Pedido A = 10
Pedido B = 5
Stock = 25

Total asignado = 40
```

No se exige identificar individualmente cada pieza. DEC-12 no fija una regla contable detallada de reparto de costos entre pedidos; la implementación conservará cantidades y causalidad suficientes para derivaciones posteriores.

### Cancelación

#### Plan `DRAFT`

- Puede cancelarse sin efectos físicos.
- No existen reservas liberadas ni consumos inventados.

#### Plan `RELEASED` sin efectos físicos confirmados

- No se asumirá automáticamente que nada ocurrió.
- Se requerirá confirmación autorizada de “sin efectos”.
- Hasta entonces permanecerá `PENDING_RECONCILIATION`.
- Las reservas se liberarán únicamente al confirmar.

#### Con efectos físicos canónicos

La cancelación no será un rollback ficticio. Deberá explicar consumo, retorno, merma, output ya producido, WIP si existió, reserva restante y disposición final.

No se restaurarán automáticamente insumos como si la producción no hubiese ocurrido. `CANCELLED` será terminal.

### Capa 2 — Living Lab futura

ZeroMerma quedará preparada para fuentes futuras como:

- sensores;
- básculas conectadas;
- hornos y equipos;
- RFID/NFC;
- lectores;
- visión por computadora;
- variables ambientales;
- modelos de inferencia;
- telemetría;
- fuentes experimentales futuras.

Estas fuentes:

- no serán requisito del core;
- no participarán obligatoriamente en el fast-path;
- no escribirán directamente inventario o estados productivos;
- no modificarán pedidos ni refunds;
- ingresarán inicialmente como observaciones;
- podrán almacenar datos brutos fuera del OLTP;
- conservarán referencias verificables y lineage.

DEC-12 no selecciona proveedor ni hardware.

### Separación entre datos canónicos y experimentales

```text
dato operativo canónico
!=
dato observado, inferido o experimental
```

Una observación experimental no podrá por sí sola:

- mover inventario;
- crear WIP;
- registrar consumo;
- registrar output;
- registrar merma;
- completar una corrida;
- cancelar una corrida;
- modificar pedidos;
- afectar la frontera `PRODUCTION_COMMITTED`;
- afectar refunds.

La única ruta permitida será equivalente a:

```text
ProductionObservation
  -> validación/promoción explícita
  -> comando de dominio
  -> evento operativo canónico
```

### Modelo de observaciones

Se utilizará un modelo append-only equivalente a:

```text
ProductionObservation
  id
  production_plan_id
  production_run_id
  production_stage_id nullable
  observation_type

  source_kind
  source_id nullable
  source_event_id nullable

  occurred_at
  recorded_at

  evidence_status
  evidence_quality
  confidence nullable

  schema_version
  instrumentation_version nullable
  model_version nullable

  payload/reference
  correlation_id nullable
  causation_id nullable
  promoted_event_id nullable
  supersedes_observation_id nullable
```

Tipos de origen mínimos:

```text
MANUAL
ZEROMERMA
INFERRED
SENSOR
EQUIPMENT
COMPUTER_VISION
EXPERIMENTAL
```

Estados de evidencia mínimos:

```text
EXPERIMENTAL
VALIDATED
REJECTED
PROMOTED
```

Calidades mínimas:

```text
MEASURED
CONFIRMED
DERIVED
ESTIMATED
CORRECTED
```

Reglas:

- `confidence` será nullable y, cuando exista, estará entre 0 y 1;
- el tipo de fuente no equivale a autoridad;
- la calidad no convierte automáticamente un dato en canónico;
- las correcciones usarán supersession, no edición destructiva;
- una observación rechazada permanecerá registrada;
- cambiar un modelo no reescribirá decisiones históricas;
- la retención y privacidad dependerán de DEC-16;
- la telemetría masiva podrá almacenarse fuera del OLTP mediante referencias verificables.

### Promoción explícita

Existirá un contrato conceptual equivalente a:

```text
promote_observation(
  observation_id,
  validation_rule_version,
  actor_or_process
)
  -> domain command
  -> canonical event
```

Invariantes:

- una observación no muta directamente el dominio;
- la regla de validación es versionada;
- el actor o proceso debe estar autorizado;
- la promoción es idempotente;
- existe auditoría y outbox;
- se conserva lineage;
- `promoted_event_id` enlaza el resultado;
- una observación rechazada no desaparece;
- no se aprueba promoción automática general.

Una promoción automática futura requerirá política explícita y evidencia suficiente.

### Identidad, timestamps y lineage

Se utilizarán identificadores estables, preferentemente UUIDv7 cuando sea compatible con las decisiones vigentes, para plan, corrida, etapa, evento, observación, fuente e instrumento.

Se distinguirá:

```text
occurred_at
= momento del hecho u observación

recorded_at
= momento de recepción o persistencia
```

Se conservarán cuando corresponda:

- `correlation_id`;
- `causation_id`;
- `source_event_id`;
- `schema_version`;
- `instrumentation_version`;
- `model_version`;
- referencia/hash del dato bruto.

Cadena conceptual:

```text
production_plan_id
  -> production_run_id
  -> production_stage_id
  -> canonical_event_id / observation_id
  -> source_id
  -> occurred_at / recorded_at
```

### Eventos canónicos

Se contemplan eventos conceptuales equivalentes a:

```text
production.plan_created
production.plan_released
production.reconciliation_requested
production.reconciled
production.input_consumed
production.input_returned
production.output_recorded
production.waste_recorded
production.completed
production.cancelled
```

Los nombres físicos podrán ajustarse. Una observación describe evidencia; un evento canónico registra un cambio de dominio autorizado. No son intercambiables.

### Idempotencia, locking y atomicidad

Como mínimo deberán ser idempotentes:

- liberación del plan;
- conciliación;
- cancelación;
- registro de output;
- registro de merma;
- promoción de observaciones.

Orden conceptual de locking:

```text
1. IdempotencyRecord
2. ProductionPlan/ProductionRun
3. reservas
4. InventoryBalance ordenados por branch/product/location
5. movimientos, asignaciones y eventos
6. auditoría/outbox
7. commit
```

Reglas:

- no habrá lock global de producción;
- corridas distintas podrán avanzar concurrentemente;
- productos y sucursales independientes no se serializarán;
- una conciliación no duplicará reservas, movimientos, output, merma, auditoría ni outbox;
- corrida, reservas, balances, movimientos, asignaciones, auditoría, outbox e idempotencia compartirán la unidad transaccional correspondiente.

### Rendimiento

La dirección técnica será:

- Production Board desde proyecciones indexadas;
- conciliación precargada;
- ausencia de escaneo completo del ledger por pantalla;
- ausencia de lock global;
- ausencia de dependencia de sensores;
- telemetría masiva fuera del fast-path;
- eventos y observaciones indexados por corrida, tiempo, fuente y estado;
- datos brutos de alta frecuencia fuera del OLTP cuando sea necesario;
- replay mediante fast-path.

DEC-12 no fija SLA sin una línea base.

### Errores conceptuales

Se registran códigos estables equivalentes a:

```text
PRODUCTION_PLAN_NOT_RELEASED
PRODUCTION_PLAN_ALREADY_RELEASED
PRODUCTION_RECONCILIATION_REQUIRED
PRODUCTION_RECONCILIATION_MISMATCH
PRODUCTION_INPUTS_UNEXPLAINED
PRODUCTION_OUTPUT_OVER_RECORDED
PRODUCTION_ALLOCATION_MISMATCH
PRODUCTION_CANCELLATION_REQUIRES_RECONCILIATION
PRODUCTION_RECIPE_VERSION_IMMUTABLE
PRODUCTION_OBSERVATION_NOT_PROMOTABLE
PRODUCTION_OBSERVATION_ALREADY_PROMOTED
```

No se implementan mediante esta decisión documental.

### Auditoría y outbox

Se auditarán como mínimo:

- plan y versión;
- corrida;
- receta/version;
- cantidades planeadas;
- demanda de pedidos y stock;
- reservas;
- consumos;
- retornos;
- merma;
- outputs;
- asignaciones;
- diferencias;
- razones;
- usuario o fuente;
- `occurred_at`;
- `recorded_at`;
- `request_id`;
- referencia idempotente;
- lineage de observación/promoción cuando corresponda.

Un replay no generará eventos de negocio duplicados.

### Relación con DEC-10

Se preserva:

```text
PRODUCTION_COMMITTED
= frontera comercial de cancelación
```

El inicio físico, plan liberado, corrida, observación, inferencia, sensor, conciliación, output o merma no modificarán retroactivamente esa frontera.

`production_started` podrá existir como dato operativo o analítico, pero no como autoridad financiera ordinaria.

### Relaciones con DEC-07 y DEC-08

DEC-07 gobierna operaciones exactly-once, replay sin duplicar efectos y causalidad por evento/movimiento.

DEC-08 gobierna ledger causal, reserva al liberar, WIP sólo con evidencia, consumo/output/merma coherentes, movimientos compensatorios, prohibición de stock negativo ordinario y locking ordenado.

DEC-12 no reinterpreta esas decisiones.

### Dependencias posteriores

```text
DEC-15 -> hardware, gateways, conectividad y offline opcionales
DEC-16 -> privacidad, cámaras, audio, datos personales y retención
DEC-17 -> continuidad, almacenamiento externo, recovery e ingesta
DEC-18 -> métricas, confianza, calidad y alertas
DEC-19 -> migración e históricos sin inventar producción real
DEC-20 -> piloto operacional y Living Lab
```

Estas decisiones no se resuelven dentro de DEC-12.

### Ajustes puntuales a tareas posteriores

Sin crear un roadmap paralelo:

- `ZM-FIN-008`: comandos, capabilities, scopes, idempotencia y lineage de producción;
- `ZM-FIN-054`: plan/corrida, reservas, WIP opcional, ledger y conciliación;
- `ZM-FIN-069`: recetas inmutables y snapshots versionados;
- `ZM-FIN-070`: Production Board y Reconciliation/Supervisor.

### Migración conceptual

1. Separar plan y corrida.
2. Crear estados de liberación y conciliación.
3. Fortalecer versión y snapshot de receta.
4. Añadir reservas al liberar.
5. Incorporar WIP opcional.
6. Crear conciliación final.
7. Sustituir consumo teórico registrado como real.
8. Crear movimientos causales de consumo, retorno, merma y output.
9. Añadir asignaciones a pedidos y stock.
10. Permitir output parcial opcional.
11. Corregir cancelación.
12. Añadir idempotencia y locking.
13. Añadir eventos canónicos.
14. Crear un módulo append-only de observaciones.
15. Crear la frontera de promoción explícita.
16. Añadir IDs, timestamps y lineage.
17. Separar Production Board de Reconciliation.
18. Actualizar OpenAPI backend-first.
19. Regenerar el cliente TypeScript.
20. Adaptar Backoffice.
21. Tratar históricos mediante DEC-19.

No se inventarán consumos, outputs, inicios, mermas o asignaciones históricas.

### Pruebas futuras obligatorias

#### Plan y reservas

- crear y liberar;
- release idempotente;
- reserva completa;
- stock insuficiente;
- cancelación `DRAFT`;
- cancelación `RELEASED` sin efectos;
- concurrencia.

#### Conciliación

- confirmar sin diferencias;
- consumo real distinto;
- retorno;
- merma;
- output distinto;
- material no explicado;
- `PENDING_RECONCILIATION`;
- replay exactly-once.

#### Receta

- versión congelada;
- edición histórica rechazada;
- nueva versión;
- UOM y snapshot.

#### Asignaciones

- varios pedidos;
- pedido más stock;
- suma exacta;
- doble asignación rechazada;
- output insuficiente;
- remanente explícito.

#### Output parcial

- uno o varios outputs;
- replay;
- conciliación final del delta;
- sobreconteo rechazado.

#### Cancelación

- sin efectos;
- con efectos;
- WIP;
- output previo;
- merma;
- reconciliación obligatoria.

#### Observaciones

- manual;
- inferida;
- sensor;
- equipo;
- visión;
- confidence;
- deduplicación por `source_event_id`;
- supersession;
- rechazo;
- promoción;
- doble promoción;
- lineage.

#### Autoridad

- observación no mueve inventario;
- observación no completa corrida;
- sensor no altera pedidos;
- inferencia no cambia refund;
- sólo un comando promovido genera evento canónico.

#### Rendimiento y concurrencia

- corridas independientes;
- sucursales independientes;
- ausencia de lock global;
- Production Board sin full ledger scan;
- telemetría fuera del fast-path.

Estas pruebas no se ejecutan ni implementan mediante esta decisión documental.

### Evidencia técnica asociada

En el código vigente:

- `ProductionBatch` mezcla plan y ejecución;
- los estados actuales exigen `IN_PROGRESS`;
- el servicio `start` registra un inicio administrativo no necesariamente físico;
- `complete` usa consumo teórico como real;
- no existen reservas ni WIP;
- la merma se oculta en varianza;
- la cancelación sólo cambia estado;
- receta/versionado no es plenamente inmutable;
- la UI actual es interactiva;
- no existe conciliación integral;
- no existen asignaciones de pedidos/stock;
- no existe módulo de observaciones;
- los timestamps no distinguen `occurred_at` y `recorded_at`;
- no existe lineage científico;
- idempotencia y locking son incompletos.

Estos hechos describen la implementación vigente y no equivalen a implementación de DEC-12.

### Consecuencias, límite e historial

- **Tareas afectadas:** `ZM-FIN-003`, `ZM-FIN-008`, `ZM-FIN-054`, `ZM-FIN-069`, `ZM-FIN-070` y las tareas posteriores del Plan Maestro que implementen producción, recetas, inventario, pedidos, observaciones, hardware, contratos, clientes o migración de datos.
- **Consecuencias:** separación plan/corrida, reservas, conciliación final, WIP opcional, recetas inmutables, movimientos causales, asignaciones explícitas, Production Board, superficie de supervisor, observaciones append-only, promoción explícita, lineage, locking, idempotencia, auditoría y outbox.
- **Dependencias:** DEC-07 para idempotencia; DEC-08 para inventario; DEC-10 para la frontera comercial `PRODUCTION_COMMITTED`; DEC-15 a DEC-20 para hardware/offline, privacidad, continuidad, calidad de datos, históricos y piloto.
- **Límite:** DEC-12 define política normativa y modelos conceptuales; no certifica que producción, reservas, WIP, conciliación, observaciones, sensores, locking, idempotencia, migraciones, contratos, Backoffice o pruebas estén implementados.
- **Historial:** `PENDIENTE` desde 2026-08-26; `APROBADA` por el propietario el 2026-08-28. La aprobación incluye operación de baja interacción, extensión Living Lab desacoplada y corridas capaces de abastecer varios pedidos y stock mediante asignaciones explícitas sin doble asignación.

## DEC-13 — Pricing y descuentos

- **Estado:** `APROBADA`
- **Fecha:** 2026-08-28
- **Propietario:** propietario de ZeroMerma
- **Contenido aprobado:** autoridad del backend, precios versionados, scope global con sustitución por sucursal, motor declarativo limitado 13-B, stacking exclusivamente explícito, prioridad, exclusiones, caps, redondeo, snapshot, cotización, ventas, pedidos, amendments, devoluciones, seguridad, idempotencia, rendimiento, migración y pruebas futuras.
- **Respuesta aprobada:** decisiones 1B, 2A, 3B, 4A, 5C y 6A, junto con las invariantes, modelos conceptuales y dependencias descritos en esta decisión.

### Separación conceptual

ZeroMerma distinguirá expresamente:

```text
base price
commercial discount/promotion
manual price or discount exception
operational deduction/charge
payment method
refund
cost
```

Invariantes:

```text
CommercialDiscount != OperationalDiscount
payment method != pricing rule
refund != new pricing calculation
cost != sale price
price/cost change != inventory movement
```

`CommercialDiscount` será una regla comercial que modifica el importe de una venta o pedido. `OperationalDiscount` continuará siendo una deducción o cargo interno y no participará en el precio comercial, subtotal, descuento ni total de ventas o pedidos.

`POS-OPDISC-01` permanecerá oculto conforme a DEC-02 hasta que nombres, contratos, navegación y presentación no puedan confundirse con promociones comerciales.

### Autoridad del backend

El backend será la única autoridad sobre:

- precio base;
- reglas candidatas;
- descuentos aplicados;
- importes bruto, descuento y neto;
- total de venta o pedido;
- identidad o fingerprint de cotización;
- snapshot confirmado.

El frontend podrá presentar una cotización y enviar su identidad, pero no podrá imponer precio, descuento o total. Toda venta, pedido y amendment terminará en una decisión de pricing validada por backend.

### Propietario del precio base

La resolución canónica será:

```text
PRODUCT_DIRECT
-> versión de precio del Product exacto

CLASS_CAPTURE
-> versión de precio de ProductClass
```

No habrá fallback silencioso entre producto y clase.

Si no existe un precio válido:

```text
PRICE_NOT_AVAILABLE
```

la operación no podrá confirmarse. Un producto o clase inactivo, no vendible o sin precio aplicable tampoco podrá confirmarse.

### Scope del precio base

La política aprobada será:

```text
global base price
+
optional branch override
```

Reglas:

1. Existirá un precio global por defecto.
2. Una sucursal podrá definir una versión que sustituya el precio global.
3. POS y pedidos de una misma sucursal utilizarán el mismo precio base.
4. No habrá precios base distintos por canal dentro de la misma sucursal.
5. Las promociones sí podrán declarar elegibilidad por canal.
6. Un override de sucursal no afectará otras sucursales.
7. Los scopes obedecerán DEC-04.
8. La administración obedecerá las capacidades de DEC-03.
9. La ausencia de scope no significará `GLOBAL`.

Orden de resolución:

```text
branch override válido
-> global válido
-> PRICE_NOT_AVAILABLE
```

Dos versiones igualmente aplicables para la misma identidad, scope y momento constituirán una configuración inválida.

### Precios versionados y vigencia

Los precios serán inmutables y versionados. Cada versión conservará como mínimo:

- producto o clase;
- importe;
- moneda;
- scope;
- sucursal cuando aplique;
- `valid_from`;
- `valid_to` nullable;
- estado;
- número o identidad de versión;
- actor;
- razón o referencia del cambio;
- timestamps.

La vigencia será un intervalo semiabierto:

```text
[valid_from, valid_to)
```

La fecha inicial será inclusiva y la final exclusiva. Las reglas configuradas con horario local usarán la timezone versionada de la sucursal y persistirán los instantes UTC utilizados.

No se permitirán solapamientos para la misma identidad, scope, sucursal y rango efectivo. Cambiar un precio creará una nueva versión y nunca editará documentos históricos.

### Precio base cero y gratuidad

La política será:

```text
active and sellable base price > 0
```

No se permitirá precio base cero para un producto o clase activo y vendible. Precio cero no podrá utilizarse para ocultar una configuración faltante.

La gratuidad se representará mediante una promoción explícita y versionada del 100 %, conservando:

- precio bruto;
- regla y versión aplicadas;
- causa;
- importe descontado;
- total neto;
- auditoría.

### Motor de promociones 13-B

Se aprueba un motor declarativo limitado. No se aprueba una DSL, código promocional arbitrario ni ejecución general de expresiones.

Las reglas podrán expresar estructuradamente:

- producto, clase, marca u otro target soportado;
- scope global o por sucursal;
- canal;
- rango de vigencia;
- porcentaje o importe fijo;
- nivel de aplicación;
- prioridad;
- grupo de exclusión;
- compatibilidad explícita;
- cantidad mínima;
- subtotal mínimo;
- límite o cap;
- precio neto mínimo;
- estado;
- versión.

Las capacidades físicas concretas podrán incorporarse progresivamente, pero no podrán contradecir esta semántica.

### Stacking, prioridad y exclusiones

La política será:

```text
no implicit stacking
```

Dos reglas sólo se acumularán cuando el modelo declare explícitamente su compatibilidad. La coincidencia entre scopes `GLOBAL`, `PRODUCT`, `CLASS`, `BRAND`, `BRANCH` o `CHANNEL` no implicará stacking.

Los grupos de exclusión representarán reglas incompatibles.

Convención normativa:

```text
lower numeric priority
=
higher precedence
```

Dentro de un mismo grupo:

- ganará la regla elegible con mayor precedencia;
- un empate de prioridad será una configuración inválida;
- no habrá desempate por UUID, fecha de creación, orden SQL o posición accidental;
- una configuración ambigua no podrá activarse.

### Orden matemático

El orden aprobado será:

```text
1. descuentos porcentuales de línea
2. descuentos fijos de línea
3. descuentos porcentuales de documento
4. descuentos fijos de documento
```

Cada descuento fijo declarará explícitamente uno de estos niveles:

```text
PER_UNIT
PER_LINE
DOCUMENT
```

El nivel no se inferirá silenciosamente. El orden matemático formará parte de la versión de la política de pricing y redondeo.

### Caps, floor y reglas inválidas

1. Un descuento no podrá exceder su base elegible.
2. El neto nunca podrá ser negativo.
3. No habrá clamp silencioso de una regla inválida.
4. Una regla inválida será rechazada o no podrá activarse.
5. Una promoción explícita del 100 % podrá producir neto cero.
6. Los caps por regla, línea o documento serán explícitos y versionados.
7. Un precio neto mínimo será explícito y versionado cuando exista.
8. DEC-13 no fija un cap o floor monetario global arbitrario.

### Redondeo y asignación de descuentos

La política será:

```text
Decimal/Numeric
monetary scale = 0.01
ROUND_HALF_UP
float prohibited
```

Cálculo conceptual:

```text
gross_line =
Q(base_unit_price * quantity)

line_percentage_discounts
-> line_fixed_discounts

net_line_before_document =
gross_line - line_discount

gross_document =
sum(gross_line)

document_percentage_discounts
-> document_fixed_discounts

net_document =
sum(net_line_before_document)
- document_discount
```

Los descuentos de documento se asignarán a líneas para soportar devoluciones, tickets y reportes. La distribución será determinista mediante:

- proporción sobre el neto elegible después de descuentos de línea;
- método de mayores restos;
- desempate estable por secuencia de línea;
- persistencia del ajuste residual.

DEC-13 no introduce impuestos de venta que no estén definidos por decisiones o contratos vigentes.

### Snapshot de pricing

Cada decisión confirmada conservará una estructura equivalente a:

```text
PricingDecision
  pricing_version
  currency
  resolved_at
  branch_id
  channel
  quote_id/fingerprint

  base_price_source
  base_price_reference/version
  base_unit_price

  candidate_discount_rule_versions
  applied_discount_rule_versions
  excluded_rule_reasons

  gross_line_amount
  line_discount_amount
  document_discount_allocation
  net_line_amount

  gross_document_amount
  total_discount_amount
  net_document_amount

  rounding_policy_version
```

El snapshot permitirá reconstruir:

- precio base y versión;
- reglas candidatas;
- reglas aplicadas;
- reglas excluidas y su razón;
- orden matemático;
- redondeo;
- importes bruto, descuento y neto.

La implementación podrá utilizar una entidad común y referencias para evitar duplicación innecesaria, sin crear una fuente paralela de verdad.

### Excepciones manuales

La política vigente será:

```text
manual price override in POS = prohibited
manual discount override in POS = prohibited
```

La cajera no podrá introducir arbitrariamente un precio, porcentaje, descuento fijo, gratuidad ni excepción ad hoc. Toda reducción procederá de una regla comercial configurada, versionada, vigente, autorizada y auditable.

`discounts.manage` administrará reglas y no concederá autoridad para alterar una venta concreta. Una futura política de overrides requerirá aprobación explícita nueva y una capacidad operativa separada.

### Cotización obsoleta

La cotización backend devolverá una identidad o fingerprint estable.

Al confirmar:

1. el backend resolverá nuevamente o validará la versión de pricing;
2. comparará el fingerprint presentado;
3. si cambió el precio o alguna regla, no cobrará silenciosamente;
4. responderá con un conflicto equivalente a:

```text
PRICE_QUOTE_STALE
HTTP 409
```

5. el frontend mostrará el nuevo total;
6. la cajera deberá aceptarlo nuevamente.

No se aprueba una ventana temporal de precio congelado. La interacción del carrito no mantendrá un lock global ni locks de base de datos abiertos.

### Ventas

La venta utilizará el motor canónico para:

- resolver precio base;
- evaluar reglas;
- calcular bruto, descuento y neto;
- validar pagos;
- persistir snapshot;
- generar ticket;
- producir auditoría y outbox;
- completar la idempotencia de DEC-07.

Persistirá como mínimo:

- subtotal bruto;
- descuento total;
- total neto;
- importes por línea;
- asignación de descuentos documentales;
- referencias y versiones aplicadas;
- `pricing_decision_id` o fingerprint equivalente.

El frontend no enviará un total autoritativo.

### Pedidos y anticipo

Se preservan las reglas de DEC-10:

- producto exacto;
- snapshot versionado;
- anticipo obligatorio del 50 %;
- amendments sólo antes de `PRODUCTION_COMMITTED`;
- históricos inmutables.

El anticipo mínimo se calculará sobre:

```text
net order_total_snapshot
```

después de aplicar pricing y promociones. Una versión confirmada conservará precios, reglas e importes aunque las reglas expiren posteriormente.

### Repricing completo de amendments

La política será:

```text
order.amend
-> reprice entire new version
using current valid prices and promotions
```

Reglas:

1. La versión anterior permanecerá inmutable.
2. Todas las líneas de la nueva versión se resolverán nuevamente.
3. No se conservarán silenciosamente precios antiguos de líneas no modificadas.
4. Se creará un snapshot completo nuevo.
5. Se recalculará el total neto.
6. Se recalculará el anticipo mínimo del 50 %.
7. Si `net_paid` queda por debajo del mínimo, deberá completarse atómicamente o se rechazará el amendment.
8. Si `net_paid` excede el nuevo total, no se generará un refund silencioso; se requerirá una operación financiera explícita y atómica.
9. Después de `PRODUCTION_COMMITTED`, el amendment continuará prohibido.

### Devoluciones y refunds

Se preservan DEC-09 y DEC-11. La base económica del refund será:

```text
original allocated net line amount
```

No se utilizarán el precio vigente, la promoción vigente, el catálogo actual ni el costo actual.

Por línea se conservará:

- cantidad original;
- bruto original;
- descuento de línea;
- asignación de descuento documental;
- neto retornable;
- cantidad retornada acumulada;
- valor retornado acumulado;
- residual de redondeo.

En una devolución parcial:

- el neto se distribuirá proporcionalmente;
- se aplicará la misma política de centavos;
- la última devolución elegible recibirá el remanente exacto;
- múltiples devoluciones nunca superarán la cantidad ni el valor neto original.

La liquidación real del refund continuará gobernada por DEC-11.

### Tickets y reportes

Los tickets mostrarán de manera reconstruible:

- precio bruto;
- promociones aplicadas;
- descuento;
- total neto;
- desglose pertinente por línea y documento.

No informarán descuento cero cuando haya existido uno.

Los reportes distinguirán:

- venta bruta;
- descuentos comerciales;
- venta neta;
- devoluciones;
- margen o costo cuando esté definido.

`OperationalDiscount` no participará en estas métricas comerciales.

### Scope y seguridad

Capacidades aplicables:

```text
pricing.view
pricing.manage
discounts.view
discounts.manage
```

Reglas:

- autorización backend deny-by-default;
- scopes conforme a DEC-04;
- una regla de sucursal no afectará otra;
- administración global requerirá `GLOBAL` explícito;
- consultar no concederá modificar;
- administrar precios no concederá administrar promociones;
- no existirá autoridad de override manual;
- activaciones, desactivaciones, conflictos y cambios sensibles serán auditables.

### Idempotencia, locking y rendimiento

DEC-07 se aplicará a las operaciones críticas. Un replay no duplicará:

- decisión de pricing;
- descuento;
- venta;
- pedido;
- amendment;
- ticket;
- auditoría;
- outbox.

No habrá lock global de pricing. Los conflictos de solapamiento se serializarán únicamente por la identidad relevante del precio o regla.

La implementación utilizará índices por:

- estado;
- moneda;
- scope;
- sucursal;
- canal;
- target;
- prioridad;
- grupo;
- rango efectivo;
- versión.

La caché será una optimización y nunca autoridad. No se escanearán históricos para calcular una venta, no se recalcularán documentos confirmados y el checkout no dependerá de Backoffice o worker. DEC-13 no fija un SLA sin baseline.

### Errores conceptuales

Se registran códigos estables equivalentes a:

```text
PRICE_NOT_AVAILABLE
PRICE_ZERO_NOT_ALLOWED
PRICE_SCOPE_CONFLICT
PRICE_VERSION_OVERLAP
PRICE_QUOTE_STALE

DISCOUNT_RULE_CONFIGURATION_INVALID
DISCOUNT_PRIORITY_CONFLICT
DISCOUNT_STACKING_NOT_ALLOWED
DISCOUNT_EXCLUSION_CONFLICT
DISCOUNT_EXCEEDS_ELIGIBLE_BASE
DISCOUNT_NET_NEGATIVE
DISCOUNT_MANUAL_OVERRIDE_NOT_ALLOWED

ORDER_REPRICING_REQUIRED
ORDER_REPRICING_OVERPAYMENT
```

La forma HTTP definitiva se concretará durante implementación; `PRICE_QUOTE_STALE` corresponderá a un conflicto `409`.

### Auditoría y outbox

Se auditarán como mínimo:

- actor;
- sucursal y scope;
- canal;
- producto o clase;
- versión de precio;
- regla y versión;
- vigencia;
- prioridad;
- compatibilidad;
- grupo de exclusión;
- importe anterior y nuevo;
- candidatas;
- reglas aplicadas;
- exclusiones y razón;
- bruto;
- descuento;
- neto;
- rounding policy;
- fingerprint;
- request ID;
- referencia idempotente no secreta;
- timestamps.

Un replay no generará eventos de negocio duplicados.

### Migración conceptual

1. Crear precios inmutables y versionados.
2. Añadir scope global y por sucursal.
3. Añadir vigencia `[from,to)`.
4. Convertir precios actuales en versiones iniciales sólo cuando sea demostrable.
5. Versionar reglas comerciales.
6. Añadir canal, grupos, compatibilidad, prioridad, nivel y caps.
7. Validar configuraciones y solapamientos.
8. Implementar el motor único del backend.
9. Añadir cotización y fingerprint.
10. Persistir `PricingDecision`.
11. Integrar ventas.
12. Integrar pedidos.
13. Integrar amendments con repricing completo.
14. Integrar devoluciones desde el snapshot original.
15. Adaptar tickets.
16. Adaptar reportes.
17. Aplicar DEC-03, DEC-04 y DEC-07.
18. Actualizar OpenAPI backend-first.
19. Regenerar cliente TypeScript.
20. Actualizar POS.
21. Actualizar Backoffice.
22. Mantener `POS-OPDISC-01` oculto.
23. Retirar estructuras mutables o paralelas después del cutover.
24. Tratar históricos ambiguos mediante DEC-19.

No se inventarán promociones o descuentos históricos.

### Pruebas futuras obligatorias

#### Precio

- producto y clase;
- global y override de sucursal;
- ausencia y cero;
- producto o clase inactivo;
- vigencia y timezone;
- solapamiento;
- rango `[from,to)`.

#### Promociones

- producto, clase, marca y global;
- sucursal y canal;
- porcentaje;
- fijo `PER_UNIT`, `PER_LINE` y `DOCUMENT`;
- prioridad y empate;
- exclusión;
- stacking permitido y prohibido;
- regla futura y expirada;
- cap y floor;
- descuento superior a la base;
- gratuidad mediante 100 %;
- configuración inválida.

#### Redondeo

- línea y documento;
- método de mayores restos;
- residual;
- cantidades decimales;
- ausencia de float.

#### Ventas

- autoridad backend;
- quote vigente y stale;
- reconfirmación;
- replay;
- snapshot;
- ticket;
- auditoría y outbox.

#### Pedidos

- anticipo del 50 % sobre neto;
- repricing completo;
- promociones modificadas;
- anticipo insuficiente tras amendment;
- sobrepago;
- amendment posterior a `PRODUCTION_COMMITTED` rechazado.

#### Devoluciones

- refund desde neto original;
- devolución parcial y múltiples devoluciones;
- descuento documental;
- último centavo;
- límite de valor.

#### Seguridad y separación

- `view` y `manage`;
- branch scope y `GLOBAL`;
- deny-by-default;
- override manual rechazado;
- `CommercialDiscount` sí afecta pricing;
- `OperationalDiscount` no afecta pricing;
- costo no cambia precio automáticamente;
- cambiar precio no mueve inventario.

### Evidencia técnica vigente

La inspección técnica asociada constató:

- el precio vigente es mutable en `Product` y `ProductClass`;
- no existen versiones ni vigencia de precios;
- los descuentos comerciales tienen CRUD y preview;
- `priority` no tiene semántica de checkout;
- ventas y pedidos no consumen `CommercialDiscount`;
- tickets registran descuento cero;
- devoluciones usan `unit_price` original sin allocations completas;
- POS y backend pueden divergir si cambia el precio;
- `OperationalDiscount` está separado en efecto, pero su nombre es ambiguo;
- la autorización actual se limita principalmente a la superficie;
- no existe idempotencia transversal ni snapshot completo.

Estos hechos describen el código vigente y no equivalen a implementación de DEC-13.

### Consecuencias, dependencias, límite e historial

- **Tareas afectadas:** `ZM-FIN-003`, `ZM-FIN-008`, `ZM-FIN-071`, `ZM-FIN-072`, `POS-OPDISC-01` y las tareas posteriores que implementen ventas, pedidos, devoluciones, tickets, reportes, contratos, clientes y migración de datos.
- **Consecuencias:** motor único de pricing en backend; precios y promociones versionados; scope global/sucursal; promociones por canal; snapshot reconstruible; cotizaciones con fingerprint; repricing completo de amendments; refunds desde el neto original; reportes bruto/descuento/neto; seguridad, idempotencia, auditoría y outbox.
- **Dependencias:** DEC-02 para mantener oculto `POS-OPDISC-01`; DEC-03 para capacidades; DEC-04 para scope; DEC-07 para idempotencia; DEC-09 para devoluciones; DEC-10 para pedidos y amendments; DEC-11 para liquidación de refunds; DEC-19 para históricos ambiguos.
- **Límite:** DEC-13 define política normativa y modelos conceptuales. No certifica implementación de pricing, promociones, snapshots, cotizaciones, ventas, pedidos, devoluciones, tickets, reportes, migraciones, contratos, clientes, seguridad ni pruebas.
- **Historial:** `PENDIENTE` desde 2026-08-26; `APROBADA` por el propietario el 2026-08-28 mediante decisiones 1B, 2A, 3B, 4A, 5C y 6A; se aprueba el motor 13-B con stacking exclusivamente explícito y se prohíben los overrides manuales en POS.

## DEC-14 — Pagos externos

- **Estado:** `APROBADA`
- **Fecha:** 2026-08-29
- **Propietario:** propietario de ZeroMerma
- **Contenido aprobado:** frontera provider-agnostic, primera integración prevista con BBVA Total POS, operación externa durable, finalización por evidencia equivalente a `CAPTURED`, incertidumbre `UNKNOWN`, resolución automática prioritaria, registro contable separado, fallback manual controlado, conciliación, seguridad, responsabilidades, idempotencia, migración y dependencias de implementación.
- **Respuesta aprobada:** decisiones 1B, 2B, 3B y 4B, junto con las invariantes, modelos conceptuales y límites descritos en esta decisión.

### Alcance aprobado

ZeroMerma evolucionará desde el registro contable actual del medio `CARD` hacia una integración real de pagos externos mediante una frontera provider-agnostic.

La primera integración prevista será:

```text
BBVA Total POS
```

El dominio financiero no dependerá directamente de BBVA. La composición conceptual será equivalente a:

```text
Sale / Order / Refund
        ↓
Payment domain
        ↓
ExternalPaymentProvider
        ↓
BBVA adapter
        ↓
BBVA Total POS
```

Agregar otro proveedor posteriormente no obligará a reescribir ventas, pedidos, devoluciones, caja o conciliación.

La selección de BBVA como primera integración prevista no certifica ni presupone todavía:

- protocolo concreto;
- SDK;
- middleware local;
- modelo exacto de terminal;
- compatibilidad con navegador o workstation;
- certificaciones;
- sandbox;
- condiciones comerciales;
- capacidades exactas de void, refund, callback, webhook o polling.

Estas dependencias deberán verificarse antes de implementar y antes del cutover.

### Separación conceptual

ZeroMerma distinguirá expresamente:

```text
CARD accounting leg
!=
provider authorization

authorization
!=
capture
!=
settlement

refund
!=
void
!=
technical reversal
!=
chargeback

provider fee
!=
sale revenue

payment method
!=
external provider operation
```

El modelo distinguirá conceptualmente:

- `Payment`;
- `PaymentLeg`;
- intención de pago externo;
- operación del proveedor;
- autorización;
- captura;
- settlement;
- void;
- refund;
- reversa técnica;
- disputa o chargeback;
- conciliación;
- fee del proveedor.

Registrar un medio `CARD` no constituye por sí mismo autorización, captura ni integración aprobada.

### Modos de ejecución

Cada operación conservará una procedencia equivalente a:

```text
ACCOUNTING_ONLY
PROVIDER_INTEGRATED
MANUAL_FALLBACK
```

Los nombres físicos podrán variar, pero las tres semánticas permanecerán separadas.

#### `ACCOUNTING_ONLY`

Representa un cobro realizado fuera de ZeroMerma. ZeroMerma registra el hecho contable, pero no afirma haber obtenido automáticamente autorización o captura del proveedor.

La interfaz y los comprobantes deberán dejar inequívoco que se trata de registro externo y no de un pago iniciado o confirmado por ZeroMerma.

#### `PROVIDER_INTEGRATED`

ZeroMerma inicia y sigue una operación mediante el adapter correspondiente. El éxito exige evidencia autoritativa del proveedor y no puede provenir de una afirmación del cliente o del operador.

#### `MANUAL_FALLBACK`

Es una vía excepcional para resolver una operación integrada incierta cuando existe evidencia verificable suficiente. No es una confirmación automática y no permite fabricar una autorización o captura.

### Vinculación automática de la operación externa

Antes de contactar a BBVA o a cualquier proveedor, ZeroMerma persistirá y vinculará la intención externa con:

- venta o pedido;
- `Payment`;
- `PaymentLeg`;
- sucursal;
- workstation;
- terminal;
- importe;
- moneda;
- `IdempotencyRecord`;
- identidad utilizada ante el proveedor.

La relación conceptual será equivalente a:

```text
Sale / Order / Refund
          ↓
       Payment
          ↓
      PaymentLeg
          ↓
ExternalPaymentOperation
          ↓
       provider
```

Cuando una respuesta se pierda, la misma operación continuará vinculada automáticamente con la misma venta, pedido, aggregate y leg:

```text
PROCESSING
   ↓
UNKNOWN
```

La cajera no creará el estado `UNKNOWN`, no reconstruirá manualmente la relación y no seleccionará a posteriori una venta a la cual asociar un cobro incierto.

### Modelo conceptual de operación externa

La implementación conservará invariantes equivalentes a:

```text
ExternalPaymentOperation
  id
  payment_leg_id/refund_leg_id
  operation_type
  execution_mode
  provider_code
  merchant_account_reference
  terminal_reference
  workstation_id
  branch_id

  local_idempotency_record_id
  provider_idempotency_key
  provider_operation_id nullable

  requested_amount
  currency
  local_status

  provider_status nullable
  provider_response_code nullable
  failure_category nullable

  requested_at
  last_attempt_at nullable
  authorized_at nullable
  captured_at nullable
  completed_at nullable

  reconciliation_status
  last_reconciled_at nullable
```

La forma física exacta podrá variar, pero deberá preservar identidad causal, procedencia, scope, estado local, evidencia externa y conciliación.

Constraints conceptuales mínimos:

```text
exactly one of payment_leg_id/refund_leg_id
requested_amount > 0
operation currency == leg currency
unique local causal effect
unique provider idempotency identity per provider account
unique non-null provider operation identity per provider account
unique callback/webhook event identity
```

Los intentos, respuestas, callbacks y cambios relevantes conservarán historia append-only o una estructura técnicamente equivalente.

### Evidencia mínima para completar

Política aprobada:

```text
PENDING / PROCESSING / UNKNOWN
!=
completed payment
```

Un leg integrado sólo se proyectará como completado cuando exista evidencia concluyente del proveedor equivalente a:

```text
CAPTURED
```

`AUTHORIZED` por sí solo no será suficiente cuando el proveedor distinga autorización de captura.

`SETTLED` pertenece a conciliación bancaria posterior y no será requisito ordinario para finalizar la venta.

Si BBVA Total POS expone una operación de venta aprobada sin separar literalmente autorización y captura, el adapter mapeará la evidencia autoritativa de BBVA a la semántica canónica equivalente a `CAPTURED` únicamente cuando demuestre que el cobro quedó efectivamente realizado.

Los nombres específicos del proveedor no se convertirán en estados del dominio.

### Máquina de estados e incertidumbre

La operación externa distinguirá como mínimo estados equivalentes a:

```text
CREATED
PROCESSING
DECLINED
UNKNOWN
FAILED
SUCCEEDED/CAPTURED
```

Cuando aplique, distinguirá además:

```text
AUTHORIZED
VOIDED
PARTIALLY_REFUNDED
REFUNDED
```

La conciliación conservará una dimensión separada equivalente a:

```text
PENDING
MATCHED
DISCREPANCY
RESOLVED
```

Reglas:

- `DECLINED` es un resultado conocido;
- `FAILED` sólo significa que existe evidencia suficiente de que no ocurrió el efecto financiero;
- un timeout con posible efecto externo produce `UNKNOWN`;
- `UNKNOWN` podrá resolverse posteriormente usando la misma identidad;
- callbacks, webhooks, consultas o respuestas tardías sólo podrán aplicar transiciones válidas y monotónicas;
- una transición tardía no reescribirá la secuencia histórica;
- una corrección utilizará un nuevo evento causal o efecto compensatorio cuando corresponda.

### Rechazo conocido

Ante un rechazo concluyente del proveedor:

```text
status = DECLINED
leg_completed = false
```

ZeroMerma:

- no considerará pagada la venta por ese importe;
- permitirá otro intento o método conforme a las reglas ordinarias;
- conservará el intento rechazado para auditoría y diagnóstico.

Un rechazo conocido no equivale a `UNKNOWN`.

### Resultado `UNKNOWN`

Caso canónico:

```text
T1 ZeroMerma persiste la operación y su identidad
T2 ZeroMerma envía el cobro a BBVA
T3 BBVA puede haber procesado el cobro
T4 la respuesta se pierde

resultado = UNKNOWN
```

Mientras la operación permanezca `UNKNOWN`:

- no se cobrará nuevamente a ciegas el mismo efecto;
- no se creará una intención nueva para el mismo efecto causal abierto;
- se conservará la identidad local y del proveedor;
- la venta conservará el vínculo con el leg incierto;
- ZeroMerma intentará consultar automáticamente al proveedor;
- se podrán usar polling, callback, webhook o reconciliación conforme a las capacidades reales de BBVA;
- el cierre se comportará conforme a DEC-06.

Invariante:

```text
UNKNOWN
!=
DECLINED
!=
permission to retry
```

DEC-14 no fija duraciones arbitrarias para resolver incertidumbre.

### Resolución automática primero

La política ordinaria será:

```text
automatic resolution first
```

Secuencia conceptual:

```text
UNKNOWN
  ↓
consulta/callback/reconciliación automática
  ↓
CAPTURED
o
DECLINED/FAILED conocido
```

La intervención humana será excepcional y sólo procederá cuando el sistema no pueda producir automáticamente evidencia concluyente.

### Fallback manual controlado

La resolución manual de una operación integrada exigirá:

- capability operativa separada;
- supervisor de la sucursal;
- mismo scope de sucursal;
- importe y moneda;
- terminal;
- referencia disponible;
- evidencia verificable del proveedor;
- motivo obligatorio;
- actor;
- timestamps;
- auditoría;
- outbox;
- estado explícitamente manual;
- conciliación obligatoria.

El supervisor:

- no crea una autorización;
- no puede marcar `CAPTURED` sólo por declaración de la cajera;
- no elimina ni sustituye la historia de `UNKNOWN`;
- sólo resuelve con evidencia verificable conforme al contrato real del proveedor.

Si no existe evidencia suficiente, la operación permanece incierta.

### Dependencia RBAC del fallback manual

La política aprobada de `MANUAL_FALLBACK` exige una autoridad operativa específica y separada.

El catálogo canónico vigente de DEC-03 contiene 55 capabilities únicas, pero todavía no incluye una capability dedicada a resolver manualmente pagos externos `UNKNOWN`.

Por tanto:

1. `cash_finance.manage` no implica autoridad para resolver `UNKNOWN -> CAPTURED` ni para ejecutar `MANUAL_FALLBACK`.
2. `config.manage`, `roles.manage`, la pertenencia a Backoffice, el rol de supervisor o cualquier otra capability existente tampoco implican por sí solos esa autoridad.
3. Antes de habilitar `MANUAL_FALLBACK` deberá incorporarse deliberadamente una capability explícita al catálogo RBAC mediante la revisión y el versionado correspondientes de DEC-03.
4. El código o nombre concreto de esa futura capability será una decisión técnica de implementación y no se inventa en DEC-14.
5. Su asignación deberá cumplir DEC-03 y DEC-04:
   - deny-by-default;
   - scope explícito;
   - no autoelevación;
   - no concesión automática al Superadministrador;
   - mínimo privilegio.
6. Hasta que esa extensión RBAC esté versionada e implementada, `MANUAL_FALLBACK` permanecerá deshabilitado.
7. Esta regla no modifica DEC-03 ni cambia el conteo canónico vigente de 55 capabilities.

La extensión del catálogo, sus asignaciones y la aplicación efectiva de scopes dependerán de las tareas RBAC y scopes `ZM-FIN-015`–`ZM-FIN-022`.

### Responsabilidades

#### Cajera

Puede:

- iniciar el cobro normal;
- ver sus estados;
- aportar comprobante o información;
- identificar la terminal utilizada;
- solicitar ayuda.

No puede resolver arbitrariamente `UNKNOWN -> CAPTURED`.

#### Supervisor de sucursal

Puede resolver excepcionalmente una operación de su sucursal únicamente mediante el fallback aprobado, con capability, scope y evidencia suficientes.

#### Soporte

Atiende conectividad, errores del adapter, consultas fallidas, webhook, polling y problemas técnicos de terminal o integración. Soporte no fabrica resultados económicos.

#### Administrador

Atiende duplicados, discrepancias materiales, capturas huérfanas, disputas, chargebacks, compensaciones y casos que exceden la autoridad del supervisor.

### Idempotencia

Conforme a DEC-07 existirá correlación entre:

```text
business Idempotency-Key
provider idempotency identity
provider operation identity
callback/webhook event identity
```

Garantías:

- como máximo un cargo por intención;
- como máximo un refund por intención;
- el replay local devuelve el resultado existente;
- una respuesta tardía no crea otra operación;
- un callback o webhook repetido no genera efectos nuevos;
- polling y callback pueden competir sin duplicar la transición;
- una key nueva no permite esquivar un `UNKNOWN` causal todavía abierto;
- `X-Request-ID` permanece sólo como trazabilidad.

La clave del proveedor, la identidad de su operación y la identidad del evento externo complementan, pero no sustituyen, la `Idempotency-Key` de negocio.

### Frontera transaccional

La integración utilizará un patrón equivalente a:

```text
TX1:
  IdempotencyRecord
  payment/refund aggregate
  leg
  external operation
  audit/outbox
  commit

external provider call:
  fuera de locks largos

TX2:
  lock de operación/agregado necesario
  validar transición
  persistir resultado y efectos
  audit/outbox
  commit
```

No habrá:

- transacción distribuida ficticia;
- llamada a BBVA bajo un lock largo de caja, pedido o inventario;
- lock global de pagos;
- éxito local antes de evidencia suficiente.

Las operaciones independientes de distintas sucursales, workstations y legs podrán avanzar concurrentemente.

### Terminal, workstation y sucursal

La política provider-agnostic exigirá:

- terminal activa;
- terminal asociada o validada para la sucursal correcta;
- snapshot de terminal, workstation y sucursal en la operación;
- ninguna selección silenciosa de una terminal equivocada;
- históricos inmutables aunque una terminal sea sustituida;
- correlación inequívoca entre callback y operación.

La topología concreta:

```text
terminal dedicada
vs
terminal compartida
```

y el mecanismo físico de comunicación se resolverán mediante DEC-15 y la validación técnica real de BBVA.

### Void, refund y reversa técnica

Invariante:

```text
void != refund != technical reversal
```

- `void` sólo se utilizará cuando BBVA o el proveedor lo soporte para una operación todavía elegible;
- `refund` será una nueva operación causal contra una captura válida;
- `technical reversal` será una compensación por inconsistencia o duplicado conforme a las capacidades del proveedor.

Se preservan DEC-09, DEC-10 y DEC-11:

- prioridad CASH-first;
- refunds parciales;
- límite acumulado;
- no exceder el derecho económico causal;
- no duplicar la devolución física;
- un refund posterior al cierre no reabre una caja histórica.

Un refund `UNKNOWN` tampoco podrá repetirse a ciegas.

### Conciliación y settlement

`CAPTURED` será la frontera operativa del pago integrado.

`SETTLED` será una dimensión posterior de conciliación bancaria.

La conciliación deberá detectar como mínimo:

- operación local coincidente;
- operación local sin evidencia externa;
- operación externa sin documento local;
- importe distinto;
- moneda distinta;
- duplicado;
- refund faltante;
- fee;
- chargeback;
- operación no encontrada.

Los estados `UNKNOWN` que puedan modificar el resultado financiero de un turno bloquearán el cierre conforme a DEC-06.

Una captura todavía no liquidada bancariamente no bloqueará por sí sola la venta o el cierre ordinario.

No se reabrirá una caja cerrada.

La resolución manual de una operación externa siempre dejará conciliación obligatoria.

### Fees

Invariante:

```text
provider fee
!=
customer sale total
```

La comisión de BBVA o de otro proveedor:

- no modificará silenciosamente el pricing de DEC-13;
- no reducirá el revenue comercial registrado;
- se representará separadamente;
- podrá formar parte de conciliación y reportes financieros.

DEC-14 no aprueba recargos al cliente.

### Seguridad

Requisitos mínimos:

- nunca almacenar PAN completo;
- nunca almacenar CVV;
- nunca almacenar track data;
- usar únicamente tokens o referencias opacas cuando corresponda;
- mantener secretos fuera del repositorio;
- separar sandbox y producción;
- usar TLS;
- validar firmas de callbacks o webhooks cuando el proveedor los soporte;
- proteger contra replay de eventos externos;
- permitir rotación de credenciales;
- minimizar payloads;
- redactar datos antes de logs, auditoría y outbox.

DEC-14 no declara cumplimiento PCI, certificación de BBVA ni certificación de hardware sin evidencia.

### Offline y relación con DEC-15

DEC-14 no autoriza pagos electrónicos offline implícitos.

```text
no evidence
!=
approval
```

Cuando ZeroMerma carezca de comunicación suficiente para conocer el resultado, la operación permanecerá pendiente o incierta según la evidencia disponible.

La estrategia de hardware, terminal offline, continuidad, workstation, middleware local y terminal compartida o dedicada se decidirá mediante DEC-15 y la verificación de la integración BBVA.

### POS

La experiencia futura distinguirá claramente:

- esperando terminal;
- aprobado;
- rechazado;
- resultado pendiente;
- requiere conciliación;
- operación contable externa;
- fallback manual;
- refund pendiente.

Reglas:

- el doble submit estará bloqueado;
- la identidad sobrevivirá reload o crash;
- `UNKNOWN` impedirá un nuevo cobro ciego;
- `DECLINED` permitirá cambiar de método;
- no se imprimirá una venta como pagada antes de evidencia suficiente;
- `Tarjeta (registro)` nunca aparentará ser un pago integrado.

### Backoffice

La superficie administrativa futura permitirá:

- localizar una operación por venta, pedido o referencia;
- ver su timeline;
- comparar estado local y del proveedor;
- identificar sucursal, workstation y terminal;
- consultar discrepancias;
- reconciliar;
- tramitar comandos permitidos;
- conservar evidencia e historial;
- aplicar scopes y capabilities.

El estado no se editará arbitrariamente para ocultar una discrepancia.

### Auditoría, outbox y observabilidad

Se registrarán eventos conceptuales equivalentes para:

- operación solicitada;
- processing;
- captured;
- declined;
- unknown;
- void;
- refund;
- refund unknown;
- reconciliación;
- discrepancia.

La auditoría conservará, sin secretos ni datos de tarjeta:

- actor;
- sucursal;
- workstation;
- terminal;
- proveedor;
- importe;
- moneda;
- referencia externa no secreta;
- estado anterior y nuevo;
- motivo o failure category;
- request ID;
- referencia idempotente;
- `occurred_at`;
- `recorded_at`.

El replay no duplicará eventos de negocio, auditoría ni outbox.

### Errores conceptuales

La implementación expondrá errores equivalentes a:

```text
EXTERNAL_PAYMENT_DECLINED
EXTERNAL_PAYMENT_UNKNOWN
EXTERNAL_PAYMENT_ALREADY_PENDING
EXTERNAL_PAYMENT_PROVIDER_UNAVAILABLE
EXTERNAL_PAYMENT_TERMINAL_INVALID
EXTERNAL_PAYMENT_EVIDENCE_REQUIRED
EXTERNAL_PAYMENT_MANUAL_RESOLUTION_FORBIDDEN

EXTERNAL_REFUND_UNKNOWN
EXTERNAL_REFUND_EXCEEDS_ELIGIBLE_AMOUNT

EXTERNAL_RECONCILIATION_DISCREPANCY
```

DEC-14 no fija todavía el contrato HTTP definitivo.

### Rendimiento y concurrencia

La implementación deberá preservar:

```text
no_global_payment_lock = true
external_calls_under_long_locks = false
different_branches_can_progress_concurrently = true
different_terminals_can_progress_concurrently = true
causal_duplicates_prevented = true
```

Las lecturas operativas utilizarán aggregates y estados materializados e indexados. No se escaneará todo el historial de proveedor para cada operación y el replay tendrá un fast-path idempotente.

### Migración conceptual

La transición seguirá una secuencia equivalente a:

1. Separar `CARD` contable de pago integrado.
2. Crear operación externa durable.
3. Integrar DEC-07.
4. Crear frontera provider-agnostic.
5. Implementar adapter BBVA después de validar el protocolo real.
6. Añadir máquina de estados.
7. Añadir recuperación de `UNKNOWN`.
8. Añadir callback, webhook o polling conforme a BBVA.
9. Añadir conciliación.
10. Integrar ventas.
11. Integrar pedidos.
12. Integrar refunds.
13. Integrar blockers de cierre.
14. Actualizar reportes.
15. Aplicar seguridad, secrets y redacción.
16. Actualizar OpenAPI backend-first.
17. Regenerar cliente TypeScript.
18. Actualizar POS.
19. Actualizar Backoffice.
20. Retirar caminos ambiguos después del cutover.
21. Tratar históricos mediante DEC-19.

No se inventarán autorizaciones, capturas, voids, refunds ni settlements históricos.

### Pruebas futuras obligatorias

La implementación deberá cubrir como mínimo:

- captura confirmada;
- rechazo;
- timeout demostrado antes del proveedor;
- timeout con posible efecto externo;
- replay con la misma key;
- key nueva contra un efecto `UNKNOWN` abierto;
- callback o webhook duplicado;
- polling y callback concurrentes;
- éxito tardío después de `UNKNOWN`;
- crash y restart;
- venta con `CASH + CARD`;
- CASH completado y CARD pendiente;
- void cuando sea elegible;
- refund total, parcial y múltiple;
- CASH-first con remanente externo;
- refund `UNKNOWN`;
- límite acumulado de refund;
- terminal inactiva o equivocada;
- operación externa sin documento local;
- documento local sin captura externa;
- cierre bloqueado por incertidumbre relevante;
- fee y net settlement separados;
- chargeback;
- fallback manual con y sin evidencia;
- scopes de sucursal;
- redacción de datos sensibles;
- sandbox frente a producción;
- ausencia de llamadas externas bajo locks largos.

### Relaciones con decisiones aprobadas

- **DEC-02:** `CARD` contable no aparentará integración real.
- **DEC-05:** credenciales de usuario y del proveedor permanecen separadas; no se registran secretos.
- **DEC-06:** efectos `UNKNOWN` financieramente relevantes bloquean cierre y no se reabren cajas cerradas.
- **DEC-07:** intención, llamadas, callbacks y replay serán idempotentes.
- **DEC-09:** devolución física y refund financiero permanecen separados.
- **DEC-10:** la operación externa materializa el derecho económico del pedido, no lo redefine.
- **DEC-11:** se preservan legs reales, CASH-first, refunds pendientes y ausencia de liquidación ficticia.
- **DEC-13:** pricing determina el importe debido; proveedor y fees no lo recalculan.

### Dependencia explícita de DEC-16

DEC-16 gobernará los requisitos externos aplicables que DEC-14 no puede aprobar por sí sola, incluidos, según correspondan al proveedor, jurisdicción y operación real:

- obligaciones de seguridad y compliance de pagos;
- alcance PCI y responsabilidades asociadas;
- retención de referencias o datos relacionados con pagos;
- privacidad;
- contenido documental o comprobantes cuando aplique;
- otros requisitos legales o regulatorios externos.

Reglas:

1. DEC-14 no declara cumplimiento PCI.
2. DEC-14 no decide ni presupone el alcance PCI definitivo.
3. DEC-14 no sustituye ni resuelve DEC-16; DEC-16 permanece `PENDIENTE`.
4. Seleccionar BBVA no constituye validación legal, contractual, regulatoria ni de compliance.
5. Antes del cutover productivo del pago integrado deberán estar aprobados, implementados y verificados los requisitos de DEC-16 que resulten aplicables.
6. Una incompatibilidad futura entre requisitos de BBVA, DEC-16 y DEC-14 se reportará explícitamente y no se resolverá reinterpretando silenciosamente DEC-14.

### Dependencias explícitas de BBVA

Permanecen pendientes de implementación o verificación:

- protocolo y contrato técnico real de BBVA Total POS;
- modelo físico de terminal;
- SDK o middleware, si existe;
- sandbox;
- credenciales;
- certificación;
- capacidades de void y refund;
- mecanismo de consulta, callback, webhook o polling;
- disponibilidad;
- restricciones comerciales;
- seguridad exigida por BBVA.

Si evidencia futura de BBVA contradice DEC-14, la política no se modificará ni reinterpretará silenciosamente: la contradicción se reportará y resolverá explícitamente.

### Evidencia técnica asociada

El código vigente al aprobar DEC-14 presenta estas brechas:

- ventas persisten `CARD` como leg contable y confirman localmente sin proveedor;
- pedidos registran pagos y refunds sin ciclo externo;
- refunds de ventas externos permanecen deshabilitados;
- no existen operaciones externas, estados de proveedor, terminal binding ni identidad externa;
- no existe idempotencia DEC-07 transversal;
- la conciliación administrativa sólo opera realmente sobre cortes de efectivo;
- el worker no procesa callbacks, polling ni reconciliación externa;
- POS muestra correctamente `Tarjeta (registro)` como registro contable;
- OpenAPI no expresa todavía operaciones externas ni sus estados.

Estos hechos describen el código vigente; no constituyen implementación de DEC-14.

### Historial y límite

- **Historial:** DEC-14 permaneció `PENDIENTE` desde 2026-08-26 y fue `APROBADA` por el propietario el 2026-08-29 mediante decisiones 1B, 2B, 3B y 4B.
- **Primera integración prevista:** BBVA Total POS mediante un adapter y dominio provider-agnostic.
- **Resolución de incertidumbre:** automática primero; intervención humana sólo como excepción controlada y con evidencia verificable.
- **Vinculación:** ZeroMerma crea y vincula automáticamente la operación externa antes de contactar al proveedor; la cajera no crea el `UNKNOWN`.
- **Límite:** DEC-14 define política e invariantes. No certifica que BBVA esté integrado, contratado, probado o disponible en producción y no implementa pagos, terminales, migraciones, contratos, clientes ni preparación productiva.

## DEC-15 — Hardware y offline

- **Estado:** `APROBADA`
- **Fecha:** 2026-08-29
- **Propietario:** propietario de ZeroMerma
- **Qué se aprueba:** bridge local provider-agnostic, matriz certificada, hardware mínimo del piloto, operación transaccional online-only, recuperación de resultados y contingencia manual externa controlada.
- **Tareas principales afectadas:** tareas de POS, impresión, scanner, cajón, terminal, conectividad y continuidad de tienda.
- **Respuesta aprobada:** decisiones `1B`, `2A`, `3B`, `4B`, `5A`, `6A` y `7B`, con las dependencias y límites que se detallan a continuación.
- **Regla:** una falla de hardware o conectividad no altera la autoridad del backend ni el resultado económico o de inventario ya confirmado.

### Principios normativos

```text
business commit
!=
device side effect
```

```text
sale confirmed
!=
ticket printed
```

```text
cash payment confirmed
!=
drawer opened
```

```text
browser print
!=
certified printer integration
```

```text
keyboard input
!=
certified scanner integration
```

```text
cached read
!=
offline transactional authority
```

```text
network error
!=
business rejection
```

```text
request not sent
!=
request sent with unknown result
!=
server commit confirmed
```

```text
local device availability
!=
backend business authority
```

```text
manual contingency outside ZeroMerma
!=
offline transaction confirmed by ZeroMerma
```

Una falla de hardware posterior al commit no revierte, repite ni altera silenciosamente el resultado económico o de inventario.

### Arquitectura aprobada: bridge local provider-agnostic

La estrategia aprobada es:

```text
POS web
  -> LocalHardwareAgent / LocalHardwareBridge
  -> device adapter
  -> printer / drawer / terminal / diagnostic capability
```

El POS continúa siendo una aplicación web. No se aprueba convertirlo en una aplicación desktop completa como requisito inicial.

El bridge será estrecho y provider-agnostic:

- no contendrá reglas de venta, pricing, caja o inventario;
- no decidirá si una venta quedó confirmada;
- no determinará estados financieros de BBVA;
- no sustituirá la autoridad del backend;
- expondrá únicamente capacidades locales estructuradas;
- utilizará adapters por protocolo o dispositivo;
- conservará identidad, versión, health y binding de workstation;
- permitirá incorporar nuevos dispositivos sin reescribir el dominio.

Modelo conceptual equivalente, sin imponer nombres físicos:

```text
LocalHardwareAgent
  identity
  workstation_binding
  version
  capabilities
  health
  paired_at
  last_seen_at
```

Capacidades iniciales potenciales:

```text
print
open_drawer
terminal_transport
device_health
```

El scanner keyboard wedge no necesita pasar obligatoriamente por el bridge.

### Seguridad del bridge

Requisitos mínimos:

- ejecución con mínimo privilegio;
- comunicación mediante loopback protegido, IPC local o equivalente;
- pairing o autenticación con la workstation;
- allowlist de la aplicación u origen autorizado;
- prohibición de aceptar comandos de cualquier sitio web;
- mensajes estructurados, no comandos arbitrarios;
- correlation e identidad causal;
- protección contra repetición;
- timeouts;
- logs sanitizados;
- secretos fuera del frontend;
- separación sandbox/producción;
- paquete e instalaciones verificables;
- actualizaciones firmadas;
- compatibilidad de versiones;
- rollback controlado;
- diagnóstico sanitizado.

Una prueba de dispositivo nunca crea una venta, pago, refund, movimiento de caja o movimiento de inventario.

### Política de soporte: matriz certificada

La política aprobada es:

```text
supported
iff
explicitly tested and versioned in the certified matrix
```

ZeroMerma no declara soporte abierto para cualquier dispositivo que parezca compatible con el sistema operativo, el navegador o un protocolo genérico.

La matriz conservará como mínimo:

```text
device_type
required_or_optional
manufacturer_model_or_protocol
connection
operating_system
browser_or_runtime
driver_version
adapter_version
workstation_binding
fallback
failure_impact
tested_status
support_status
validated_at
```

Los modelos, versiones y familia concreta de sistema operativo y navegador se seleccionarán durante inventario físico, implementación y piloto. DEC-15 no inventa marcas o versiones aún no probadas.

Una combinación fuera de la matriz podrá clasificarse como `UNSUPPORTED`, `EXPERIMENTAL`, `PENDING_VALIDATION` o equivalente, pero nunca se presentará como soportada.

### Hardware obligatorio y opcional del piloto

Será obligatorio en una caja POS:

- workstation compatible;
- navegador o runtime certificado;
- pantalla o monitor;
- impresora de tickets certificada.

La pantalla táctil no será obligatoria si teclado y mouse permiten operar correctamente la experiencia POS.

Serán opcionales:

- scanner;
- cajón de efectivo;
- display de cliente;
- otros periféricos no esenciales.

La ausencia de scanner o cajón no impedirá utilizar el POS cuando exista un procedimiento operativo alternativo válido.

La terminal BBVA será obligatoria únicamente en las workstations donde se habilite `PROVIDER_INTEGRATED`. Una caja que opere sólo con otros medios permitidos no requerirá terminal BBVA.

La exigencia documental, fiscal o de comprobantes continúa sujeta a DEC-16. Una incompatibilidad deberá reportarse explícitamente.

### Impresión y ticket

La secuencia normativa es:

```text
business commit
  -> immutable document/ticket available
  -> print request with causal identity
  -> bridge/adapter execution
  -> independent local outcome
```

Reglas:

1. La impresión ocurre después del commit del negocio.
2. Un fallo de impresión no revierte la venta, pedido, devolución o cierre.
3. Un retry de impresión no repite la operación económica.
4. La reimpresión usa el mismo snapshot histórico e inicia un nuevo intento físico.
5. Los intentos y reimpresiones serán auditables cuando corresponda.
6. Una impresora sin papel u offline produce un problema operacional.
7. El sistema no afirmará `PRINTED` sin evidencia del adapter.
8. El diálogo del navegador no acredita impresión física.
9. Caracteres, corte de papel y comandos específicos pertenecen al adapter certificado.
10. El comprobante ZeroMerma y el comprobante BBVA permanecen conceptualmente separados, salvo que capacidades verificadas y DEC-16 aprueben una composición diferente.

`window.print()` podrá mantenerse temporalmente como fallback no certificado o de compatibilidad, pero no será evidencia de impresión exitosa ni el camino soportado principal del piloto.

### Reimpresión

La reimpresión:

- no modifica el documento original;
- no recalcula precios, promociones o importes;
- no vuelve a ejecutar la venta;
- crea un nuevo intento físico;
- conserva actor, motivo y timestamp cuando la política lo requiera;
- no abre el cajón;
- no inicia un nuevo pago;
- no cambia la conciliación.

La autorización y retención de tickets o datos personales dependen de DEC-16.

### Política del cajón de efectivo

La política aprobada es:

```text
automatic causal opening for confirmed CASH effects
+
controlled supervised manual opening
```

La apertura automática:

- ocurre sólo después de un efecto `CASH` confirmado que requiera acceso físico;
- se ejecuta como máximo una vez por efecto causal autorizado;
- no ocurre por una venta únicamente `CARD`;
- no ocurre por una reimpresión;
- no vuelve a ocurrir por replay de la venta;
- en una operación `MIXED`, corresponde al leg `CASH`, no a la clasificación `MIXED`;
- no se repite ciegamente ante timeout del dispositivo.

Pueden ser operaciones causales una venta con efectivo, refund en efectivo, pago operativo con entrada o salida física y otros movimientos `CASH` autorizados.

El fallo del cajón no revierte ni duplica el efecto financiero confirmado.

La apertura manual exige:

- autoridad backend explícita;
- scope de sucursal;
- razón obligatoria;
- actor;
- workstation;
- timestamp;
- auditoría;
- comando causal estructurado.

No se concede por pertenecer simplemente a Backoffice ni por tener un rol denominado supervisor.

La implementación deberá mapear la apertura manual a una capability explícita de DEC-03. Si el catálogo vigente no contiene una capability adecuada, se requerirá una extensión controlada antes de habilitarla. No se reutilizará silenciosamente una capability existente ni se inventa ahora su nombre.

Hasta que esa autoridad esté versionada e implementada, la apertura manual desde ZeroMerma permanecerá deshabilitada.

### Scanner

La política inicial es:

```text
scanner optional
keyboard_wedge baseline
```

Reglas:

- el POS seguirá siendo operable táctilmente, con teclado o búsqueda;
- un scanner no será autoridad de negocio;
- una doble lectura no podrá confirmar dos efectos financieros;
- el foco será controlado;
- la lectura durante modales o acciones incompatibles se ignorará o manejará explícitamente;
- un código inexistente no se sustituirá silenciosamente por otro producto;
- la operación manual seguirá disponible;
- soporte HID/API directo requerirá adapter y matriz certificada.

Que un dispositivo se comporte como teclado no equivale a scanner certificado.

### Terminal BBVA dedicada por workstation

La topología inicial aprobada es:

```text
one dedicated BBVA terminal per integrated workstation
```

Está sujeta a validación técnica real con BBVA Total POS.

Cada binding conservará:

- terminal;
- workstation;
- sucursal;
- cuenta o afiliación de proveedor cuando corresponda;
- vigencia;
- configuración o versión;
- estado activo;
- última validación;
- health;
- actor del cambio.

Reglas:

- no habrá selección silenciosa de otra terminal;
- una terminal inactiva o asociada a otra sucursal no podrá utilizarse;
- sustituir una terminal no reescribirá históricos;
- la operación externa conservará snapshot de terminal y workstation;
- el bridge podrá transportar comandos sólo si el protocolo real de BBVA lo requiere;
- el bridge no decidirá `CAPTURED`, `DECLINED` o `UNKNOWN`;
- los estados económicos continúan gobernados por DEC-14.

Si BBVA demuestra que esta topología no es técnicamente soportada, deberá reportarse la contradicción y revisarse explícitamente. No se cambiará silenciosamente a terminal compartida.

### Binding y configuración de dispositivos

Modelo conceptual:

```text
Branch
  -> Workstation
  -> DeviceBinding
  -> Device
  -> Capability
  -> AdapterConfigurationVersion
```

Cada binding indicará:

- tipo de dispositivo;
- identidad;
- conexión;
- scope de sucursal;
- workstation;
- exclusividad o compartición;
- adapter;
- versión;
- estado activo;
- health;
- fecha de vigencia;
- fallback;
- última prueba;
- actor del cambio.

Un dispositivo compartido futuro utilizará lease o serialización por dispositivo, nunca un lock global.

### Diagnóstico

La herramienta futura comprobará separadamente:

- API;
- sesión;
- sucursal;
- workstation;
- bridge;
- versión y compatibilidad;
- impresora;
- cajón;
- scanner;
- terminal;
- último error;
- configuración;
- health;
- logs sanitizados.

```text
non_destructive_health_check
!=
physical_action
!=
financial_operation
```

Probar el cajón no lo abrirá sin una acción autorizada. Probar la terminal no ejecutará un cobro real implícito.

### Política offline aprobada

La política es:

```text
transactional_mode = ONLINE_ONLY
```

Sin conexión no se confirmarán dentro de ZeroMerma:

- ventas;
- pagos `CASH`;
- pagos externos;
- pedidos;
- anticipos;
- devoluciones;
- refunds;
- merma;
- transferencias;
- producción;
- ajustes de inventario;
- apertura o cierre de caja;
- administración Backoffice.

No se implementará inicialmente:

- una cola de mutaciones offline;
- ventas locales pendientes de sincronización;
- ledgers locales;
- pricing local autoritativo;
- stock local autoritativo;
- autenticación offline;
- una réplica transaccional completa.

No existe aprobación electrónica offline implícita.

### Lecturas cacheadas opcionales

Podrán implementarse posteriormente lecturas cacheadas limitadas, como catálogo básico no sensible, información informativa de productos, Production Board y otros snapshots expresamente aprobados.

Toda lectura cacheada mostrará origen, versión, `last_synced_at`, estado stale y ausencia de autoridad transaccional.

Reglas:

- precio cacheado no autoriza checkout;
- promoción cacheada no autoriza descuento;
- stock cacheado no autoriza venta;
- Production Board cacheado es informativo;
- pedidos, tickets, clientes y datos personales no se cachean por defecto;
- cifrado, retención y limpieza dependen de DEC-16.

La caché no sustituye PostgreSQL ni al backend como autoridad.

### Sesión y autorización online

Se preservan DEC-03, DEC-04 y DEC-05:

- no existe autenticación offline implícita;
- no se utiliza usuario genérico;
- no existe operación anónima;
- no se infiere `GLOBAL`;
- una sesión expirada, bloqueada o revocada no autoriza mutaciones;
- datos cacheados no conservan autoridad indefinida;
- el bearer actual persistido en `localStorage` no se utiliza como mecanismo offline.

El bearer persistido actual es una brecha de implementación frente a DEC-05, no una capacidad aprobada por DEC-15.

Un lease offline o una credencial de contingencia requerirían una nueva decisión explícita y no quedan aprobados.

### Reconexión y resultados inciertos

La experiencia distinguirá conceptualmente:

```text
NOT_SENT
SENDING
PENDING_RESULT
CONFIRMED
REJECTED
```

Los nombres físicos podrán variar.

- Antes de enviar, la intención permanece `NOT_SENT` y puede enviarse con su misma `Idempotency-Key`.
- Durante el envío o después de enviar sin respuesta, permanece `PENDING_RESULT`; no se genera una key nueva y el POS consulta al backend con la identidad existente.
- Después del commit, la consulta recupera `CONFIRMED` y no repite el efecto.
- Un rechazo de negocio se distingue de un error de red.
- Refresh, crash, dos pestañas o reconexión convergen a la misma intención conforme DEC-07.

```text
network error
!=
business rejection
```

### Cola offline

Con la política online-only:

```text
offline_mutation_queue = disabled
```

No se almacenarán mutaciones económicas pendientes en IndexedDB, `localStorage` u otra cola local.

Una futura política offline limitada requeriría una nueva revisión y, como mínimo, allowlist explícita de comandos, UUIDv7/`Idempotency-Key` durable, cifrado, usuario, sucursal, workstation, scope, contrato versionado, orden causal, coordinación entre pestañas, recuperación tras reboot, límites de almacenamiento, resolución de conflictos, logout, revocación y limpieza segura.

Nada de ello queda aprobado ahora.

### Contingencia manual externa

La política aprobada es:

```text
controlled manual contingency outside ZeroMerma
```

No constituye una transacción offline confirmada por ZeroMerma.

La contingencia podrá utilizarse únicamente cuando ZeroMerma o la conectividad impidan operar y exista un procedimiento aprobado con supervisor, folio controlado, hora, sucursal, operador, productos, cantidades, importes, medios, evidencia del cobro, captura posterior y conciliación.

La posterior incorporación deberá:

- usar una identidad idempotente;
- preservar `occurred_at` y `recorded_at`;
- identificar el origen como contingencia;
- detectar duplicados;
- revalidar inconsistencias;
- no inventar estados BBVA;
- no inventar stock o pricing histórico;
- no sobrescribir datos conflictivos silenciosamente.

La contingencia manual permanecerá deshabilitada hasta que:

- DEC-16 determine requisitos legales, documentales, fiscales, de privacidad y retención aplicables;
- DEC-17 determine continuidad, recuperación e infraestructura;
- DEC-20 valide el procedimiento en el piloto.

Mientras esas condiciones no estén resueltas, la política efectiva ante indisponibilidad es suspender la operación transaccional.

La contingencia aprobada no autoriza incumplir requisitos externos.

### Efectos locales durante desconexión

Una vez confirmado un documento en backend, sus efectos físicos locales pendientes podrán continuar o recuperarse mediante su identidad causal, por ejemplo imprimir un ticket confirmado, reintentar una impresión fallida o consultar el resultado del print job.

Esto no autoriza nuevas mutaciones económicas offline. Un documento no confirmado no podrá imprimirse como venta pagada.

### Instalación y actualización

La arquitectura permitirá:

- instalación verificable;
- pairing por workstation;
- configuración versionada;
- compatibilidad POS/bridge/adapter;
- actualización firmada;
- rollout controlado;
- rollback;
- diagnóstico de versión;
- bloqueo únicamente de la capacidad incompatible;
- no actualizar durante una operación local activa;
- coexistencia temporal de versiones sólo dentro de una matriz compatible.

Sistema operativo, distribución productiva, observabilidad y canal de actualización dependen parcialmente de DEC-17. La validación por sucursal y rollout dependen de DEC-20.

### Experiencia POS

La UX deberá:

- mostrar estado de red y periféricos;
- diferenciar no enviado, pendiente, rechazado y confirmado;
- presentar errores accionables;
- evitar doble toque y duplicación;
- recuperar operaciones tras refresh;
- marcar datos stale;
- permitir reimpresión desde documento inmutable;
- distinguir capacidad degradada de fallo de negocio;
- no bloquear el flujo por un dispositivo opcional;
- no cambiar el resultado financiero por una falla física;
- mantener `Tarjeta (registro)` separada de BBVA integrado.

### Responsabilidades

La cajera podrá ver estados, cambiar papel, reintentar una impresión, utilizar teclado o búsqueda cuando el scanner falle, reportar una falla e iniciar contingencia únicamente conforme al procedimiento autorizado. No podrá inventar un resultado financiero, abrir el cajón arbitrariamente, modificar bindings, instalar adapters o ignorar una sesión inválida.

El supervisor podrá autorizar procedimientos permitidos, gestionar contingencia cuando esté habilitada, solicitar apertura manual del cajón sólo con autoridad explícita y coordinar conciliación y soporte.

Soporte resolverá bridge, pairing, adapters, drivers, versiones, impresora, scanner, terminal, conectividad técnica, actualización y rollback. Soporte no fabricará ventas, pagos o estados financieros.

El administrador gestionará configuración y matriz, bindings, rollout, discrepancias relevantes, autorizaciones RBAC y casos que excedan la sucursal.

### Rendimiento y concurrencia

```text
no_global_hardware_lock=true
business_fast_path_not_blocked_by_optional_device=true
hardware_failure_does_not_duplicate_business_effect=true
```

Además:

- impresión y cajón ocurren fuera del commit;
- health polling será acotado;
- un dispositivo compartido futuro se serializará por dispositivo;
- la caché será sólo read-only;
- reconexión consultará identidades pendientes;
- el bridge no escaneará todo el historial;
- una actualización no ocurrirá dentro del camino de venta;
- workstations y sucursales independientes progresarán concurrentemente.

DEC-15 no fija SLA sin hardware objetivo y baseline.

### Errores conceptuales

Se registrarán códigos equivalentes a:

```text
HARDWARE_AGENT_UNAVAILABLE
HARDWARE_AGENT_VERSION_INCOMPATIBLE
HARDWARE_AGENT_PAIRING_INVALID

PRINTER_UNAVAILABLE
PRINTER_OUT_OF_PAPER
PRINT_RESULT_UNKNOWN
PRINT_JOB_ALREADY_COMPLETED

CASH_DRAWER_UNAVAILABLE
CASH_DRAWER_MANUAL_OPEN_FORBIDDEN
CASH_DRAWER_RESULT_UNKNOWN

SCANNER_INPUT_INVALID
DEVICE_BINDING_INVALID
DEVICE_NOT_CERTIFIED

NETWORK_OFFLINE_TRANSACTION_FORBIDDEN
NETWORK_RESULT_PENDING
OFFLINE_MUTATION_NOT_SUPPORTED

MANUAL_CONTINGENCY_NOT_ENABLED
MANUAL_CONTINGENCY_EVIDENCE_REQUIRED
MANUAL_CONTINGENCY_RECONCILIATION_REQUIRED
```

Los contratos HTTP o IPC definitivos se concretarán durante implementación.

### Auditoría y observabilidad

Se auditarán cuando corresponda:

- binding y cambios de configuración;
- pairing;
- versión;
- instalación o actualización;
- health;
- print request/result;
- reimpresión;
- cajón automático/manual;
- motivo y actor;
- terminal y workstation;
- contingencia;
- reconexión;
- discrepancia;
- request ID;
- idempotency/correlation;
- `occurred_at`;
- `recorded_at`.

No se registrarán secretos, datos de tarjeta ni payloads sensibles.

### Relaciones con decisiones aprobadas

- **DEC-02:** una pantalla, botón o texto no acredita soporte físico inexistente.
- **DEC-03 y DEC-04:** capacidades explícitas, mínimo privilegio, scope backend y deny-by-default gobiernan bridge, bindings y aperturas manuales.
- **DEC-05:** sesiones online server-side; no autenticación offline implícita ni secretos en almacenamiento inseguro.
- **DEC-06:** fallo físico no revierte una operación confirmada; resultados financieros inciertos bloquean cierre cuando corresponda.
- **DEC-07:** mutaciones críticas y recuperación usan identidad idempotente durable; no blind retry.
- **DEC-08:** caché local no autoriza stock ni movimientos; backend y locking conservan autoridad.
- **DEC-10 y DEC-13:** pricing, cotización, stock, pedidos y anticipos se resuelven online por backend.
- **DEC-12:** producción no depende de sensores obligatorios y las observaciones no mutan directamente el dominio.
- **DEC-14:** BBVA permanece provider-agnostic; DEC-15 sólo define transporte, binding, health y contingencia local.

### Dependencias posteriores

- **DEC-16:** datos personales cacheados, cifrado, retención local, tickets, comprobantes, documentos de contingencia y obligaciones legales, fiscales o de privacidad. DEC-15 no resuelve DEC-16.
- **DEC-17:** topología productiva, disponibilidad, recuperación, distribución, observabilidad, actualización, continuidad y disaster recovery. DEC-15 no fija RPO/RTO ni infraestructura final.
- **DEC-19:** backfill de contingencia, históricos ambiguos, evidencia incompleta y migración de configuraciones.
- **DEC-20:** hardware concreto del piloto, versiones certificadas, validación física, procedimiento de contingencia, rollout y métricas de soporte.

DEC-16, DEC-17, DEC-19 y DEC-20 permanecen `PENDIENTE`.

### Dependencias de implementación

Permanecen pendientes:

- inventario físico de dispositivos;
- modelos concretos;
- familia OS/browser;
- bridge e instalador;
- drivers y adapters;
- pairing;
- matriz versionada;
- print jobs;
- cajón;
- terminal BBVA;
- health y diagnóstico;
- actualización;
- pruebas físicas;
- documentación operativa.

DEC-15 no certifica ningún dispositivo por el solo hecho de aprobar la arquitectura.

### Migración conceptual

1. Inventariar dispositivos y plataformas reales.
2. Versionar la matriz certificada.
3. Crear abstracción provider-agnostic de dispositivos.
4. Implementar el bridge local.
5. Crear pairing y binding por sucursal/workstation.
6. Implementar print jobs y reimpresión.
7. Implementar cajón causal.
8. Mantener keyboard wedge e integrar scanners certificados.
9. Integrar transporte local BBVA sólo si el contrato real lo exige.
10. Añadir health y diagnóstico.
11. Añadir recuperación de resultados.
12. Mantener mutaciones offline deshabilitadas.
13. Añadir caché read-only sólo donde se apruebe.
14. Corregir sesión POS conforme a DEC-05.
15. Integrar DEC-07.
16. Añadir auditoría y observabilidad.
17. Crear instalación, actualización y rollback.
18. Actualizar OpenAPI backend-first cuando aplique.
19. Regenerar el cliente.
20. Actualizar POS.
21. Documentar contingencia.
22. Validar hardware objetivo.
23. Coordinar DEC-16, DEC-17, DEC-19 y DEC-20.

No se inventará soporte, integración o certificación histórica.

### Pruebas futuras obligatorias

Sin ejecutar ahora, se deberán cubrir:

#### Impresión

- impresora ausente;
- sin papel;
- offline;
- resultado desconocido;
- reimpresión;
- duplicación;
- crash después del commit;
- documento histórico.

#### Cajón

- operación `CASH`;
- operación `CARD`;
- operación `MIXED`;
- replay;
- fallo;
- apertura manual autorizada y denegada;
- intento desde origen no autorizado.

#### Scanner

- lectura correcta;
- producto inexistente;
- doble lectura;
- foco;
- modal de pago;
- fallback teclado;
- scanner no certificado.

#### Bridge

- ausente;
- pairing inválido;
- origen no permitido;
- versión incompatible;
- adapter faltante;
- actualización interrumpida;
- rollback;
- logs sanitizados.

#### Red y recuperación

- desconexión antes de enviar, durante envío y después del commit;
- respuesta perdida;
- refresh;
- dos pestañas;
- dos workstations;
- sesión expirada;
- usuario bloqueado;
- scope revocado.

#### Offline

- mutación rechazada;
- caché stale;
- precio y stock cacheados sin autoridad;
- Production Board cacheado;
- ausencia de cola local.

#### BBVA

- terminal dedicada correcta;
- terminal inactiva;
- binding equivocado;
- bridge caído;
- sin aprobación offline;
- `UNKNOWN` gobernado por DEC-14.

#### Contingencia

- no habilitada;
- autorizada;
- folio duplicado;
- evidencia incompleta;
- captura posterior;
- conflicto;
- conciliación;
- requisitos DEC-16/17 pendientes.

#### Rendimiento

- sucursales y workstations independientes;
- ausencia de lock global;
- dispositivo opcional fuera del fast path;
- health polling acotado.

### Historial y límite

- DEC-15 permaneció `PENDIENTE` desde 2026-08-26.
- Fue aprobada por el propietario el 2026-08-29.
- Las decisiones aprobadas fueron `1B`, `2A`, `3B`, `4B`, `5A`, `6A` y `7B`.
- El bridge es provider-agnostic.
- El soporte se limita a una matriz certificada.
- La operación transaccional es online-only.
- La contingencia manual es externa y condicionada.
- No se aprobó una cola offline ni una aplicación desktop completa.

DEC-15 define política, arquitectura e invariantes. No certifica que el bridge exista, una impresora esté integrada, el cajón funcione, un scanner esté soportado, BBVA esté conectado, exista operación offline, exista contingencia habilitada o el hardware del piloto haya sido validado.

## DEC-16 — Requisitos externos

- **Estado:** `PENDIENTE`
- **Propietario:** propietario de ZeroMerma
- **Qué debe aprobarse:** jurisdicción, ticket, privacidad, retención, exportación, comunicaciones y consentimiento.
- **Tareas principales afectadas:** tareas fiscales, legales, de documentos, comunicaciones, privacidad y reportes del Plan Maestro.
- **Respuesta aprobada:** ninguna.
- **Regla:** ninguna recomendación técnica sustituye aprobación legal o del propietario.

## DEC-17 — Continuidad

- **Estado:** `PENDIENTE`
- **Propietario:** propietario de ZeroMerma
- **Qué debe aprobarse:** plataforma, dominios, RPO/RTO, retención de backup y criterios de DR.
- **Tareas principales afectadas:** tareas de infraestructura, despliegue, backup, restore, observabilidad y recuperación.
- **Respuesta aprobada:** ninguna.
- **Regla:** el entorno local no constituye una plataforma productiva aprobada.

## DEC-18 — Métricas y alertas

- **Estado:** `PENDIENTE`
- **Propietario:** propietario de ZeroMerma
- **Qué debe aprobarse:** definiciones KPI, severidades, owners y condiciones accionables.
- **Tareas principales afectadas:** tareas de dashboard, reportes, alertas, worker y observabilidad.
- **Respuesta aprobada:** ninguna.
- **Regla:** métricas estáticas o metadata de reportes no constituyen KPI aprobados.

## DEC-19 — Datos existentes

- **Estado:** `PENDIENTE`
- **Propietario:** propietario de ZeroMerma
- **Qué debe aprobarse:** qué bases y datos deben migrarse, backfillearse y reconciliarse.
- **Tareas principales afectadas:** tareas de migraciones, backfills, reconciliación, inventario, caja y despliegue.
- **Respuesta aprobada:** ninguna.
- **Regla:** la línea base preservada no aprueba la calidad ni migración de datos existentes.

## DEC-20 — Piloto y rollout

- **Estado:** `PENDIENTE`
- **Propietario:** propietario de ZeroMerma
- **Qué debe aprobarse:** sitio piloto, cadencias representativas, criterios de stop y estrategia de expansión.
- **Tareas principales afectadas:** tareas de piloto, estabilización y producción general del Plan Maestro.
- **Respuesta aprobada:** ninguna.
- **Regla:** ninguna capacidad visible pendiente de validación está autorizada para piloto o producción por esta decisión.
