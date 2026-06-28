import MouseCursor from './MouseCursor';
const ELEMENT_CURSORS_MAP = Symbol('ElementCursorsMap');
function initElementCursor(element, cursor) {
    _getElementCursors(element)[0] = cursor;
    _setElementCursor(element, cursor);
}
function _setElementCursor(element, cursor) {
    const cursors = _getElementCursors(element);
    cursors[1] = cursors[0];
    cursors[0] = cursor;
    element.style.cursor = (cursor instanceof MouseCursor
        ? cursor
        : MouseCursor.getDefinedCursor('auto')).getStyleProperty();
}
function resetElementCursor(element) {
    return;
    //_setElementCursor(element, _getElementCursors(element)[1]);
}
function hideElementCursor(element) {
    return;
    //_setElementCursor(element, MouseCursor.getDefinedCursor('none'));
}
function _getElementCursors(element) {
    let map = _getElementCursors[ELEMENT_CURSORS_MAP];
    if (!(map instanceof WeakMap)) {
        map = new WeakMap();
        Object.defineProperty(_getElementCursors, ELEMENT_CURSORS_MAP, {
            value: map,
        });
    }
    let cursors = map.get(element);
    if (!cursors) {
        cursors = [null, null];
        map.set(element, cursors);
    }
    return cursors;
}
export { initElementCursor, resetElementCursor, hideElementCursor, _setElementCursor as setElementCursor, };
