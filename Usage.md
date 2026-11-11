# Uso

## Primera vez

1. **Carpeta compartida**: elegir con **Examinar…** dónde van a vivir los datos
   reales (otro disco o una carpeta sincronizada en la nube sirven). No hace
   falta que exista: se crea al sincronizar. Mientras no la elijas, arriba se
   ve un aviso.
2. **Autodetectar** (Ctrl+D): busca los emuladores en sus rutas estándar
   (también Flatpak) y las instalaciones portables en todos los discos. El
   resultado se agrupa por unidad → emulador → carpetas y archivos. La casilla
   de cada grupo tiene tres estados: vacía = nada, cuadrado = lo recomendado,
   tilde = todo (un clic pasa al siguiente). **Agregar seleccionados** solo
   suma a la configuración: todavía no se mueve ni se enlaza nada.
3. **Verificar estado** (F5): revisa cada carpeta y archivo y lo muestra en la
   tabla. Es de solo lectura.
4. **Sincronizar selección** (Ctrl+E) o **Sincronizar todo**: mueve los datos a
   la carpeta compartida y deja un enlace en el lugar original. **Detener**
   cancela al terminar la carpeta actual, para no dejarla a medias.

## Qué significa cada estado

| Estado | Qué pasa |
|--------|----------|
| Enlazado | Todo bien: el emulador usa la carpeta compartida. |
| Pendiente de enlazar / de migrar | Se resuelve al sincronizar. |
| Respaldado (copia al día) | Archivo suelto copiado en `_archivos/`. |
| Falta local / Enlace roto | Revisar la ruta del emulador; sincronizar lo repara. |
| Enlace dañado (archivo marcador) | Un programa de copia dejó un archivo en vez del enlace; sincronizar lo repara. |
| Apunta a otra carpeta compartida | El enlace va a una carpeta compartida distinta de la elegida. |

Los números de arriba (enlazado, pendiente, con problemas) resumen la tabla.

## Emuladores

- **Añadir / Editar / Eliminar**: cargar a mano un emulador (identificador, ruta
  por sistema, carpetas y archivos a enlazar). **Eliminar** solo lo saca de la
  lista y pide confirmación; no toca tus datos.
- **Todos / Ninguno**: tildar o destildar la lista. Lo tildado es lo que se
  verifica, sincroniza o elimina.
- Doble clic en un emulador: **restaurar un backup** en la carpeta compartida.

## Opciones

- **Backup de seguridad antes de enlazar**: antes de reemplazar una carpeta por
  el enlace guarda una copia. Si el backup falla, la carpeta no se toca.
- **Comprimir backups (.zip)**: un zip por emulador y sincronización, en
  `<compartida>/Backup-EmuLinks/<emulador>/`.
- **Backups a conservar por emulador**: los más viejos se borran solos
  (0 = conservar todos).
- **Migrar carpetas nuevas a compartida**: si una carpeta existe solo en el
  emulador, la copia a la compartida antes de enlazarla.
- **Modo simulación**: muestra en el registro qué haría, sin modificar nada.

## Configuración y ayuda

- **Configuración** (Ctrl+, o el ícono arriba a la derecha):
  - *General*: tema oscuro o claro e idioma (se aplican al reiniciar) y la
    carpeta de registros del programa.
  - *Autodetección*: carpetas extra donde buscar emuladores portables.
- **Archivo → Abrir carpeta de configuración**: dónde está `config.json`.
- **Acerca de** (F1): versión y datos del sistema, con botón para copiarlos al
  reportar un problema.

## Atajos

| Acción | Atajo |
|--------|-------|
| Autodetectar | Ctrl+D |
| Verificar estado | F5 |
| Sincronizar selección | Ctrl+E |
| Configuración | Ctrl+, |
| Acerca de | F1 |
| Salir | Ctrl+Q |
