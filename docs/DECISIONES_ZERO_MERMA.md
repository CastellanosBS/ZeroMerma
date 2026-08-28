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

- **Estado:** `PENDIENTE`
- **Propietario:** propietario de ZeroMerma
- **Qué debe aprobarse:** momento de afectación de PRODUCT_DIRECT y CLASS_CAPTURE, reservas, UOM y política de stock negativo.
- **Tareas principales afectadas:** tareas de ledger de inventario, ventas, pedidos, transferencias, producción, devoluciones y merma.
- **Respuesta aprobada:** ninguna.
- **Regla:** la persistencia actual no constituye aprobación de sus invariantes.

## DEC-09 — Devolución y merma

- **Estado:** `PENDIENTE`
- **Propietario:** propietario de ZeroMerma
- **Qué debe aprobarse:** restock, cuarentena, waste o no-stock; SEND_TO_WASTE y reglas de reversa.
- **Tareas principales afectadas:** tareas de devoluciones, correcciones, merma e inventario del Plan Maestro.
- **Respuesta aprobada:** ninguna.
- **Regla:** ninguna clasificación estática sustituye esta decisión funcional.

## DEC-10 — Pedidos

- **Estado:** `PENDIENTE`
- **Propietario:** propietario de ZeroMerma
- **Qué debe aprobarse:** momento de reconocimiento financiero y físico, reserva, pago parcial, entrega y cancelación.
- **Tareas principales afectadas:** tareas de pedidos, caja, inventario y conciliación del Plan Maestro.
- **Respuesta aprobada:** ninguna.
- **Regla:** el ciclo implementado no aprueba su semántica económica.

## DEC-11 — Pago mixto

- **Estado:** `PENDIENTE`
- **Propietario:** propietario de ZeroMerma
- **Qué debe aprobarse:** definición métrica y conteo o conciliación por medio.
- **Tareas principales afectadas:** tareas de pagos, pedidos, reportes, caja y cierre del Plan Maestro.
- **Respuesta aprobada:** ninguna.
- **Regla:** los renglones de pago actuales no constituyen una definición aprobada.

## DEC-12 — Producción

- **Estado:** `PENDIENTE`
- **Propietario:** propietario de ZeroMerma
- **Qué debe aprobarse:** semántica de cancelación, consumo, output, merma, rendimiento y receta versionada.
- **Tareas principales afectadas:** tareas de producción, recetas, costos e inventario del Plan Maestro.
- **Respuesta aprobada:** ninguna.
- **Regla:** ninguna inferencia de `ZM-FIN-002` constituye decisión de producción.

## DEC-13 — Pricing y descuentos

- **Estado:** `PENDIENTE`
- **Propietario:** propietario de ZeroMerma
- **Qué debe aprobarse:** vigencia, prioridad, acumulación, límites, redondeo y autorización de excepciones.
- **Tareas principales afectadas:** tareas de pricing y descuentos del Plan Maestro; `POS-OPDISC-01`.
- **Respuesta aprobada:** ninguna.
- **Regla:** la administración de reglas o el nombre actual de descuentos operativos no aprueban su semántica.

## DEC-14 — Pagos externos

- **Estado:** `PENDIENTE`
- **Propietario:** propietario de ZeroMerma
- **Qué debe aprobarse:** proveedor o terminal, fallback manual, reversas, estados pendientes y responsabilidades.
- **Tareas principales afectadas:** tareas de pagos, devoluciones, conciliación y hardware del Plan Maestro.
- **Respuesta aprobada:** ninguna.
- **Regla:** registrar un medio CARD no constituye una integración aprobada.

## DEC-15 — Hardware y offline

- **Estado:** `PENDIENTE`
- **Propietario:** propietario de ZeroMerma
- **Qué debe aprobarse:** matriz de dispositivos, bridge o agente local, alcance offline/reconnect y contingencia.
- **Tareas principales afectadas:** tareas de POS, impresión, scanner, cajón, terminal, conectividad y continuidad de tienda.
- **Respuesta aprobada:** ninguna.
- **Regla:** browser print y keyboard wedge no constituyen aprobación de la matriz de hardware.

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
