# hrevn-workflow

Repo público:
- https://github.com/ai-human-andalusia/hrevn-workflow

## Qué es

`hrevn-workflow` ha quedado como un **SDK Python local-first** para:

- checkpointar workflows de IA por pasos
- reanudar desde el último paso válido
- detectar cambios o tampering en outputs
- exportar un `workflow_manifest.json`
- y, cuando hay credenciales HREVN, **emitir un HREVN Verified Record real**

La propuesta de valor final del repo es:

> Checkpoint your AI workflows locally. Resume from the last valid step. Optionally generate a verifiable execution record.

---

## Posicionamiento final en GitHub

### Nombre
- `hrevn-workflow`

### Description
- `Local-first Python SDK to checkpoint AI workflows, resume from the last valid step and optionally generate verifiable execution records.`

### Versión
- `0.1.0`

### Licencia
- `Proprietary`

### Python
- `>=3.10`

---

## Qué promete

### Sí hace
- checkpoints locales por paso
- resume determinista
- hashing SHA-256 de inputs y outputs
- export de manifest
- verificación de integridad
- CLI de inspección y diagnóstico
- certificación HREVN integrada en el flujo
- telemetría local mínima
- resumen local de telemetría

### No hace
- no es dashboard
- no es SaaS
- no es workflow engine
- no es observabilidad enterprise
- no sube telemetría por detrás
- no necesita API key para funcionar localmente

---

## Arquitectura conceptual

El repo ha quedado colocado así dentro del ecosistema HREVN:

1. problema:
   - workflow continuity
2. solución técnica:
   - `hrevn-workflow`
3. diferenciación:
   - HREVN Verified Record

Links públicos asociados:
- Workflow continuity: https://hrevn.com/en/workflow-continuity/
- Verifiable AI records: https://hrevn.com/en/verifiable-ai-records/

---

## Estructura principal del repo

```text
hrevn-workflow/
  README.md
  LICENSE
  pyproject.toml
  src/hrevn_workflow/
    __init__.py
    certification.py
    checkpoint.py
    cli.py
    config.py
    errors.py
    hashing.py
    manifest.py
    storage.py
    workflow.py
  examples/
    basic_ai_pipeline.py
    vendor_due_diligence_pipeline.py
    input_document.txt
    vendor_brief.txt
  tests/
    test_workflow_basic.py
    test_checkpoint_hashing.py
    test_resume.py
    test_manifest_export.py
    test_verify.py
    test_certification.py
    test_telemetry.py
    test_cli.py
  docs/
    release_candidate_internal_2026-05-02.md
    publication_readiness_checklist_2026-05-02.md
```

---

## Núcleo funcional

## 1. Workflow local
El SDK crea una carpeta `.hrevn/` con el estado local del workflow.

Estructura base:

```text
.hrevn/
  workflow_state.json
  checkpoints/
  manifests/
  certification/
  telemetry/
```

### Qué guarda
- estado del workflow
- checkpoints por paso
- manifest exportado
- estado de certificación
- telemetría local mínima

---

## 2. Checkpoints por paso
Cada paso puede:
- ejecutarse
- completarse
- saltarse si ya era válido
- volver a ejecutarse si cambian inputs o falla integridad

La lógica central es:
- si el paso ya estaba bien y nada cambió, `should_run()` devuelve `False`
- si cambió algo, devuelve `True`

---

## 3. Resume
El repo demuestra correctamente:

- primera ejecución -> `executed`
- segunda ejecución -> `skipped`

Ese comportamiento está validado con:
- tests automáticos
- ejemplos reales de uso

---

## 4. Integridad
El SDK:
- calcula hashes SHA-256
- encadena checkpoints
- detecta si un output cambia después
- bloquea la construcción del payload verificable si la integridad está rota

Esto evita:
- certificar estado corrupto
- o seguir como si nada tras tampering

---

## 5. Manifest
El SDK exporta:

- `workflow_manifest.json`

Incluye:
- cadena de pasos
- estado
- conteo de pasos completados/fallidos
- último paso válido
- deliverables certificables

---

## 6. Certificación HREVN integrada
La certificación no quedó como add-on raro, sino integrada en el flujo.

Secuencia real:
1. termina el workflow local
2. se exporta el manifest
3. se verifica integridad local
4. se construye el payload
5. se llama a `api.hrevn.com`
6. se guarda el resultado localmente

### Estado local guardado
En:
```text
.hrevn/certification/status.json
```

Con campos tipo:
- `status`
- `ok`
- `bundle_id`
- `record_id`
- `download_url`
- `error`

### Semántica final
- si no hay credenciales: `not_configured`
- si falla remoto: `failed`
- si va bien: `generated`

Y lo importante:
- **el fallo remoto no invalida el workflow local sano**

---

## CLI final

El repo ha quedado con esta CLI:

### Estado e inspección
- `status`
- `history`
- `inspect-step`
- `list-deliverables`

### Manifest e integridad
- `manifest`
- `verify`
- `doctor`
- `record-payload`

### Estado local
- `reset`

### Telemetría local
- `telemetry-summary`

---

## Qué devuelve cada comando

### `status`
Resumen del workflow actual:
- pasos
- último paso válido
- estado de certificación

### `history`
Cadena completa de pasos:
- checkpoint hash
- previous hash
- número de inputs/outputs
- estado

### `inspect-step`
Detalle de un paso concreto:
- inputs
- outputs
- metrics
- hashes

### `list-deliverables`
Lista de outputs certificables:
- filename
- role
- path
- hash corto
- tamaño
- existencia

### `manifest`
Exporta el `workflow_manifest.json`

### `verify`
Comprueba integridad del workflow y manifest

### `doctor`
Chequeo rápido del estado operativo:
- manifest
- checkpoints
- verify
- certification

### `record-payload`
Construye el payload compatible con HREVN Verified Record

### `reset`
Resetea estado total o desde un paso

### `telemetry-summary`
Resume la telemetría local:
- installation id
- workflows iniciados
- manifests exportados
- doctor runs
- certificaciones por estado
- último evento

---

## Ejemplos incluidos

## 1. `basic_ai_pipeline.py`
Simula un caso de AI review:

1. documento fuente
2. extracción de texto
3. análisis mock tipo LLM
4. case JSON
5. client review report
6. client packet
7. manifest

Outputs:
- `extracted_text.md`
- `analysis.json`
- `intake_case.json`
- `client_review_report.md`
- `client_packet.json`
- `workflow_manifest.json`

## 2. `vendor_due_diligence_pipeline.py`
Simula due diligence de proveedor:

1. vendor brief
2. vendor summary
3. risk assessment JSON
4. follow-up questions
5. due diligence memo
6. manifest

Outputs:
- `vendor_summary.md`
- `vendor_risk_assessment.json`
- `vendor_follow_up_questions.md`
- `vendor_due_diligence_memo.md`
- `vendor_workflow_manifest.json`

---

## Telemetría

## Qué quedó implementado
Telemetría **local-only**:
- `.hrevn/telemetry/installation.json`
- `.hrevn/telemetry/events.jsonl`

### Qué registra
- inicialización de workflow
- export de manifest
- `doctor`
- cambios de certificación
- `reset`

### Qué no hace
- no hay backend específico de telemetría
- no sube eventos a HREVN por defecto

### Excepción importante
Si el usuario ejecuta certificación HREVN:
- se incluye `installation_id` en la petición de certificación

Eso permite medir:
- uso certificado real del SDK

sin romper la promesa local-first.

---

## Validación y calidad

## Tests
La suite quedó validada con:
- `29 passed`

Cobertura práctica:
- workflow básico
- hashing
- resume
- manifest export
- verify
- certification
- telemetry
- CLI

## Validación real hecha
Además de tests, se validó:
- instalación limpia
- ejecución de ejemplos
- CLI real
- certificación live contra `api.hrevn.com`
- generación real de:
  - `bundle_id`
  - `record_id`
  - `download_url`

---

## Estado de publicación

## GitHub
El repo quedó:
- separado
- limpio
- público
- con README ya orientado a developer

## PyPI
No quedó como prioridad inmediata.
La decisión final fue:
- GitHub público: sí
- PyPI: posterior si se quiere

---

## README final
El README quedó con framing:

### Entrada
- workflow continuity
- local-first
- resume
- tamper detection

### Segunda capa
- HREVN Verified Record

### Links de negocio
- workflow continuity
- verifiable AI records

O sea:
- utilidad primero
- diferenciación después

---

## Qué mide hoy de verdad
Lo más importante a nivel negocio/técnico:

El SDK ya puede medirse por:
- uso local
- y, sobre todo, por **uso certificado real** vía HREVN

Esto permite saber:
- cuántas veces el SDK llega a certificación
- cuántos workflows distintos
- cuántos runs distintos

---

## Resumen final

`hrevn-workflow` ha quedado como:

- un SDK Python pequeño
- local-first
- serio
- demostrable
- con CLI suficiente
- con ejemplos creíbles
- con integridad verificable
- con certificación HREVN real integrada
- y con framing público correcto para developers

En una frase:

> No quedó como demo conceptual, sino como herramienta usable que resuelve continuidad de workflows y añade verificación HREVN cuando hace falta.
