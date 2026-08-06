# Second Brain Integration - Instrucciones para SOUL.md

Agrega esta seccion a tu `~/.hermes/SOUL.md`:

```markdown
## Second Brain - Memoria Persistente

Eres parte de un sistema de memoria persistente llamado Second Brain.
Tu proyecto tiene un `.second-brain/` en su raiz que contiene decisiones,
aprendizajes, convenciones y arquitectura documentada.

### Al Iniciar una Sesion

Antes de comenzar trabajo significativo, lee el contexto del proyecto:

```bash
node /home/keyz/.local/share/mimocode/second-brain/src/read-notes.js <project-name>
```

Esto te da acceso a decisiones previas, aprendizajes y convenciones del proyecto.
Usa este contexto para evitar repetir errores y mantener consistencia.

### Al Finalizar una Sesion

Escribe un resumen de la sesion:

```bash
node /home/keyz/.local/share/mimocode/second-brain/src/write-note.js \
  <project-name> session "Titulo de la sesion" "hermes" "Resumen de lo trabajado, decisiones tomadas, y aprendizajes encontrados."
```

### Durante la Trabajo - Eventos Significativos

Cuando ocurra un evento significativo, escribe una nota:

**Decision tecnica:**
```bash
node /home/keyz/.local/share/mimocode/second-brain/src/write-note.js \
  <project-name> decisiones "titulo-slug" "hermes" "Descripcion de decision y razones"
```

**Aprendizaje / Hallazgo:**
```bash
node /home/keyz/.local/share/mimocode/second-brain/src/write-note.js \
  <project-name> aprendizajes "titulo-slug" "hermes" "Descripcion del aprendizaje"
```

**Convencion / Estandar:**
```bash
node /home/keyz/.local/share/mimocode/second-brain/src/write-note.js \
  <project-name> convenciones "titulo-slug" "hermes" "Descripcion de la convencion"
```

**Diseno de arquitectura:**
```bash
node /home/keyz/.local/share/mimocode/second-brain/src/write-note.js \
  <project-name> arquitectura "titulo-slug" "hermes" "Descripcion del diseno"
```

### Delegacion a Workers (delegate_task)

Cuando delegues trabajo via `delegate_task`, incluye en la mision del worker
estas instrucciones de escritura. El worker debe escribir en `.second-brain/`
como parte de su entrega final.

Tipos de nota: session, decisiones, aprendizajes, convenciones, arquitectura
```
