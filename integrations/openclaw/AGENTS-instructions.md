# Second Brain Integration - Instrucciones para Workspace AGENTS.md

Agrega esta seccion al `AGENTS.md` de tu workspace/proyecto:

```markdown
## Second Brain - Memoria Persistente

Este proyecto usa un sistema de memoria persistente llamado Second Brain.
El proyecto tiene un `.second-brain/` en su raiz que contiene decisiones,
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
  <project-name> session "Titulo de la sesion" "openclaw" "Resumen de lo trabajado, decisiones tomadas, y aprendizajes encontrados."
```

### Durante la Trabajo - Eventos Significativos

Cuando ocurra un evento significativo, escribe una nota:

**Decision tecnica:**
```bash
node /home/keyz/.local/share/mimocode/second-brain/src/write-note.js \
  <project-name> decisiones "titulo-slug" "openclaw" "Descripcion de decision y razones"
```

**Aprendizaje / Hallazgo:**
```bash
node /home/keyz/.local/share/mimocode/second-brain/src/write-note.js \
  <project-name> aprendizajes "titulo-slug" "openclaw" "Descripcion del aprendizaje"
```

**Convencion / Estandar:**
```bash
node /home/keyz/.local/share/mimocode/second-brain/src/write-note.js \
  <project-name> convenciones "titulo-slug" "openclaw" "Descripcion de la convencion"
```

**Diseno de arquitectura:**
```bash
node /home/keyz/.local/share/mimocode/second-brain/src/write-note.js \
  <project-name> arquitectura "titulo-slug" "openclaw" "Descripcion del diseno"
```

Tipos de nota: session, decisiones, aprendizajes, convenciones, arquitectura
```
