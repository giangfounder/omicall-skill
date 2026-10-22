# Đoạn mã chạy trong trang OMI (browser pane)

Dùng khi user đã đăng nhập trong browser pane và không có MCP. Gọi API ngay trong trang để token không rời trình duyệt; chỉ trả bản tóm tắt (kết quả lớn bị cắt hoặc tràn ngữ cảnh). Mỗi lô gọi đọc lại token (trang tải lại có thể đổi token; lỗi 401 "Error Occurred!!!" = token cũ). Tôn trọng tenant: ít lượt tải trang, không crawl giao diện.

## 1. Token + tenant
```js
const c=document.cookie.split('; ').find(x=>/_omicrm_(io|com)=/.test(x));
const T=JSON.parse(decodeURIComponent(c.split('=').slice(1).join('=')))["2"];
const P=JSON.parse(atob(T.split('.')[1].replace(/-/g,'+').replace(/_/g,'/')));
window.__t=T; window.__T=P.tenant_id;
const H={Authorization:'Bearer '+T,'Content-Type':'application/json'}, B='https://chatbot-gateway-v1-stg.omicrm.com/';
({tenant:P.tenant_id, domain:P.domain, exp:new Date(P.exp*1000).toISOString()})
```

## 2. Khảo sát kịch bản và Kho tri thức
```js
// (dán khối §1 trước)
const L=(await (await fetch(B+'callbot/script/list-by-tenant/'+window.__T,{headers:H})).json()).payload;
const IE=(await (await fetch(B+'callbot/intent/list-by-tenant/'+window.__T,{headers:H})).json()).payload;
const ET=(await (await fetch(B+'callbot/entity-type/search',{method:'POST',headers:H,body:JSON.stringify({page:1,size:100,keyword:'',tenantId:window.__T,isSearch:true,with_entity_data_type:true})})).json()).payload.items;
const TR=(await (await fetch(B+'callbot/training/search_v3?page=1&size=1',{method:'POST',headers:H,body:JSON.stringify({keyword:'',tenantId:window.__T})})).json()).payload;
const HI=(await (await fetch(B+'callbot/training/history/search?page=1&size=2',{headers:H})).json()).payload.items;
({scripts:L.map(s=>[s.id,s.name,s.type,s.version,s.uuid,s.nodes.length]),
  intents:IE.map(i=>[i.id,i.code,i.name,i.system_intent_id]), entities:ET.map(e=>[e.id,e.code,e.name,e.entity_data_types]),
  trainings:TR.total_items, history:HI.map(h=>h.status+' '+h.total_trainings)})
```

## 3. Đếm câu huấn luyện theo ý định
Server trả tối đa 50 câu/trang → duyệt đủ `total_pages` (vài chục lượt nhẹ, chỉ làm khi cần quyết định bù câu).
```js
let all=[],p=1;for(;;p++){const r=(await (await fetch(B+'callbot/training/search_v3?page='+p+'&size=100',{method:'POST',headers:H,body:JSON.stringify({keyword:'',tenantId:window.__T})})).json()).payload;all=all.concat(r.items||[]);if(!(r.items||[]).length||all.length>=r.total_items)break}
const code={};(await (await fetch(B+'callbot/intent/list-by-tenant/'+window.__T,{headers:H})).json()).payload.forEach(i=>code[i.id]=i.code);
const cnt={};all.forEach(t=>{const k=code[t.intent_id]||t.intent_id;cnt[k]=(cnt[k]||0)+1});cnt
```

## 4. Theo dõi nhập file và huấn luyện
```js
const st=(await (await fetch(B+'callbot/training/upload_excel/status/<session>',{headers:H})).json()).payload; // session: bắt từ response upload_excel
const h=(await (await fetch(B+'callbot/training/history/search?page=1&size=1',{headers:H})).json()).payload.items[0];
({upload:[st.completed,st.successTotalRecord,st.total,st.errorTotalRecord], training:h.status+' '+h.total_trainings})
```
Bắt session khi bấm "Tải lên File Excel": gắn hook XHR trước khi bấm, lọc URL chứa `upload_excel`.

## 5. Lưu payload kịch bản lớn (clipboard + dán thật)
1. PowerShell: `$t=[IO.File]::ReadAllText("<payload.json>",[Text.Encoding]::UTF8); Set-Clipboard -Value $t`
2. Trong trang tạo ô dán:
```js
let ta=document.getElementById('__pasteBox');if(!ta){ta=document.createElement('textarea');ta.id='__pasteBox';
ta.style.cssText='position:fixed;left:0;top:0;width:100vw;height:100vh;z-index:2147483647;background:#ffc';document.body.appendChild(ta);
ta.addEventListener('paste',e=>{window.__payload=e.clipboardData.getData('text');e.preventDefault();ta.value='OK '+window.__payload.length})}
ta.focus();'ready'
```
3. Windows-MCP `Screenshot` → tìm vùng vàng (nhân hệ số ảnh thu nhỏ: `kích thước gốc / kích thước ảnh`) → `Click` vào đó → `Shortcut ctrl+v`.
4. Kiểm tra rồi lưu:
```js
const j=JSON.parse(window.__payload); document.getElementById('__pasteBox')?.remove();
// cập nhật: lấy bản mới nhất làm gốc — j.id/j.uuid phải là của bản mới nhất trong list-by-tenant
const fd=new FormData();fd.append('file',new Blob([window.__payload],{type:'application/json'}),'blob');
const r=await fetch(B+'callbot/script/add_v2',{method:'POST',headers:{Authorization:'Bearer '+window.__t},body:fd});const k=await r.json();
({code:k.status_code,id:k.payload?.id,uuid:k.payload?.uuid,ver:k.payload?.version,nodes:k.payload?.nodes?.length,conn:k.payload?.connections?.length})
```
Sửa nhỏ (đổi câu, đổi đích, bố cục) không cần dán: GET bản mới nhất trong trang, sửa bằng JS, `add_v2` lại (giữ `id`+`uuid`).

## 6. Kiểm tra kịch bản đã lưu
```js
const s=(await (await fetch(B+'callbot/script/get/<id>',{headers:H})).json()).payload;const N={};s.nodes.forEach(n=>N[n.id]=n);
const bad=s.nodes.flatMap(n=>(n.next_nodes||[]).filter(t=>!N[t]).map(t=>n.id+'->'+t));
const noNext=s.nodes.filter(n=>n.node_type==='CONDITION'&&(n.return_contents||[]).length&&!(n.next_nodes||[]).length).length;
const x=s.nodes.filter(n=>n.actions&&n.actions[0].type==='TRANSFER_CALL').map(n=>n.actions[0].data.ids);
const anhChi=JSON.stringify(s.nodes).match(/anh\/chị/gi)?.length||0;
({ver:s.version,newest:s.is_newest_version,nodes:s.nodes.length,conn:s.connections.length,badRefs:bad.length,retNoNext:noNext,transferIds:x,anhChi})
```
Trình biên tập chỉ vẽ node trong khung nhìn → kiểm tra bằng API. Sau khi lưu chuyển tab editor sang id mới (`/ai/callbot/script/update/<id>`).

## 7. Đo chiều cao node để xếp bố cục (tuỳ chọn)
```js
const d={};document.querySelectorAll('.react-flow__node').forEach(n=>d[n.getAttribute('data-id')]=n.offsetHeight);d
```
Node ngoài khung nhìn không có trong DOM → `build_callflow.py` ước lượng `120 + 90 × số nhánh`.
