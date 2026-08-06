# Worker Mission Template - Second Brain

Cuando delegues una tarea via `delegate_task`, incluye esta seccion
en la mision del worker:

```markdown
## Second Brain - Captura de Conocimiento

Como parte de tu entrega, documenta en el Second Brain del proyecto:

1. **Antes de comenzar**: Lee el contexto existente:
   ```bash
   node /home/keyz/.local/share/mimocode/second-brain/src/read-notes.js <project-name>
   ```

2. **Durante el trabajo**: Si encuentras un bug, descubres una solucion,
   o tomas una decision tecnica, escribe una nota:
   ```bash
   node /home/keyz/.local/share/mimocode/second-brain/src/write-note.js \
     <project-name> aprendizajes "titulo-slug" "hermes-worker" "Descripcion"
   ```

3. **Al finalizar**: Escribe un resumen de tu trabajo:
   ```bash
   node /home/keyz/.local/share/mimocode/second-brain/src/write-note.js \
     <project-name> session "Titulo del trabajo realizado" "hermes-worker" "Resumen completo"
   ```

El proyecto tiene `.second-brain/` en su raiz. Si no existe, las notas
se crearan automaticamente.
```
