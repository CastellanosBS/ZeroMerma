# Decisiones canónicas de ZeroMerma

**Condición:** única fuente versionada para registrar `DEC-01`–`DEC-20` y sus futuras revisiones.
**Propietario de las decisiones:** propietario de ZeroMerma.
**Última actualización:** 2026-08-26.
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

- **Estado:** `PENDIENTE`
- **Propietario:** propietario de ZeroMerma
- **Qué debe aprobarse:** catálogo de capacidades, superadministrador, separación de funciones y quién administra roles.
- **Tareas principales afectadas:** `ZM-FIN-015`–`ZM-FIN-022`, según la distribución del Plan Maestro.
- **Respuesta aprobada:** ninguna.
- **Regla:** ninguna inferencia de `ZM-FIN-002` constituye decisión sobre RBAC.

## DEC-04 — Scopes

- **Estado:** `PENDIENTE`
- **Propietario:** propietario de ZeroMerma
- **Qué debe aprobarse:** roles globales o scoped, múltiples sucursales y operaciones centralizadas permitidas.
- **Tareas principales afectadas:** `ZM-FIN-015`–`ZM-FIN-022`, según la distribución del Plan Maestro.
- **Respuesta aprobada:** ninguna.
- **Regla:** ninguna inferencia de `ZM-FIN-002` constituye decisión sobre scopes.

## DEC-05 — Sesión

- **Estado:** `PENDIENTE`
- **Propietario:** propietario de ZeroMerma
- **Qué debe aprobarse:** cookie segura, intercambio de un solo uso u otro mecanismo; duración, refresh, revocación y terminal compartida.
- **Tareas principales afectadas:** tarea de sesión correspondiente del Plan Maestro; `POS-BO-01`; tareas de seguridad relacionadas.
- **Respuesta aprobada:** ninguna; el traspaso actual de bearer mediante URL no está autorizado para producción.
- **Regla:** ninguna inferencia de `ZM-FIN-002` constituye la solución de sesión.

## DEC-06 — Cierre

- **Estado:** `PENDIENTE`
- **Propietario:** propietario de ZeroMerma
- **Qué debe aprobarse:** qué comando gana ante venta o pago concurrente, si se permite cierre sin conteo y cómo se tratan pendientes.
- **Tareas principales afectadas:** tareas de caja, concurrencia y cierre del Plan Maestro.
- **Respuesta aprobada:** ninguna.
- **Regla:** la existencia de `CashCloseScreen` no aprueba la semántica de cierre.

## DEC-07 — Idempotencia

- **Estado:** `PENDIENTE`
- **Propietario:** propietario de ZeroMerma
- **Qué debe aprobarse:** generador, scope y retención de claves; respuesta ante la misma clave con payload distinto.
- **Tareas principales afectadas:** tareas de idempotencia y operaciones económicas del Plan Maestro.
- **Respuesta aprobada:** ninguna.
- **Regla:** el bloqueo de doble clic observado no constituye una política de idempotencia aprobada.

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
