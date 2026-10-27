# React Flow — DOM selectors cheatsheet cho OMIFlow

Bảng selector CSS/DOM để thao tác OMIFlow qua JavaScript trong browser pane.

## Nodes
- Tất cả node: `document.querySelectorAll('.react-flow__node')`
- Mỗi node có `.dataset.id` (ID nội bộ, dạng chuỗi random 10 ký tự VD `ZfD7IsKTHL`).
- Vị trí: `node.getBoundingClientRect()` → `{x, y, width, height}`.
- Text: `node.textContent` (bao gồm tên nút + nội dung).

## Handles (điểm nối edge)
- Tất cả handle: `document.querySelectorAll('.react-flow__handle')`
- `dataset.handlepos`: `top` / `left` / `right` / `bottom`.
- `dataset.handleid`: ID case cho Điều kiện (VD `"1"`, `"2"`, hoặc chuỗi random).
- Vị trí: `handle.getBoundingClientRect()`.

## Edges (đường nối)
- Tất cả edge: `document.querySelectorAll('.react-flow__edge')`
- SVG path bên trong: `.react-flow__edge-path`.

## Toolbar hover trên node được select
Xuất hiện bên phải node khi node được select (click 1 lần vào giữa card, drawer CHƯA mở):
- Nút thêm liền kề: gần `title="Thêm nút liền kề"` hoặc icon `+`.
- Nút sao chép: `title="Sao chép"`.
- Nút lưu kho: `title="Lưu vào kho nút"`.
- Nút xóa: `button[aria-label="Xóa node"]`.

## Zoom / Pan controls
Góc dưới trái canvas:
- Zoom in: `button[aria-label="zoom in"]`
- Zoom out: `button[aria-label="zoom out"]`
- Fit view: `button[aria-label="fit view"]`
- Toggle interactivity (khoá canvas): `button[aria-label="toggle interactivity"]`

## Kéo edge qua JS (KHÔNG khuyến nghị)
Cách chính để nối hai nút có sẵn là `left_click_drag` của công cụ trình duyệt từ chấm nguồn tới chấm đích (`ui-build-and-test.md` mục 7, đã kiểm chứng); không được thì sửa `next_nodes` + `edges.connections` trong JSON rồi lưu nháp. Giả lập PointerEvent dưới đây thường không ăn (`ui-build-and-test.md` mục 6), chỉ giữ làm tham khảo khi cần đọc toạ độ handle.

```js
function fire(el, type, x, y) {
  el.dispatchEvent(new PointerEvent(type, {
    bubbles: true, cancelable: true,
    pointerType: 'mouse', button: 0, buttons: 1,
    clientX: x, clientY: y, screenX: x, screenY: y
  }));
}

async function connectHandles(srcSelector, tgtSelector) {
  const handles = document.querySelectorAll('.react-flow__handle');
  // Xác định src và tgt theo index hoặc filter
  const src = /* handle nguồn */;
  const tgt = /* handle đích */;
  const s = src.getBoundingClientRect();
  const t = tgt.getBoundingClientRect();
  const sx = s.x + s.width/2, sy = s.y + s.height/2;
  const tx = t.x + t.width/2, ty = t.y + t.height/2;

  fire(src, 'pointerdown', sx, sy);
  await new Promise(r => setTimeout(r, 50));
  for (let i = 1; i <= 10; i++) {
    const mx = sx + (tx - sx) * i / 10;
    const my = sy + (ty - sy) * i / 10;
    fire(document.elementFromPoint(mx, my) || document.body, 'pointermove', mx, my);
    await new Promise(r => setTimeout(r, 20));
  }
  fire(tgt, 'pointerup', tx, ty);
}
```

## Xoá node qua JS
```js
// 1. Select node bằng click programmatic
const node = Array.from(document.querySelectorAll('.react-flow__node'))
  .find(n => n.dataset.id === 'TARGET_ID');
const r = node.getBoundingClientRect();
const x = r.x + 10, y = r.y + 10;
['pointerdown','pointerup','click'].forEach(t => {
  node.dispatchEvent(new PointerEvent(t, {
    bubbles: true, cancelable: true, pointerType: 'mouse',
    clientX: x, clientY: y, button: 0
  }));
});
await new Promise(r => setTimeout(r, 400));

// 2. Bấm nút xóa trong toolbar hover
document.querySelector('button[aria-label="Xóa node"]').click();
```

## Đọc data internal của React Flow (khó — không public API)
React Flow lưu state trong context không expose ra DOM dataset. Nếu cần đọc/set state trực tiếp, phải hack qua `__reactFiber` (rủi ro, không stable). Tránh — dùng DOM selectors + dispatch events là đủ cho hầu hết use case.

## Viewport mapping (browser pane 800×xxx vs actual viewport 1142×962)
Coordinates từ `getBoundingClientRect()` là **actual viewport coords**. Browser pane tools nhận **screenshot coords** với scale ≈ 0.7 (800/1142). Khi thao tác qua screenshot → nhân 0.7. Khi qua JS → dùng actual coords trực tiếp (không cần scale).
