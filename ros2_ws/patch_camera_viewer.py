from pathlib import Path
import re
import sys

TARGET = Path.home() / "mobile_robot/ros2_ws/src/amr_ai/amr_ai/web/engineer_web_server.py"
if len(sys.argv) > 1:
    TARGET = Path(sys.argv[1]).expanduser()

s = TARGET.read_text()

# 1) Layout 60/40 and fix camera title overlap
s = s.replace("grid-template-columns:55fr 45fr;", "grid-template-columns:60fr 40fr;")
s = s.replace("grid-template-columns: 55fr 45fr;", "grid-template-columns:60fr 40fr;")

if ".camera-card .display-title" not in s:
    css_insert = r'''
    .camera-card .display-title {
      position:static;
      top:auto;
      left:auto;
      margin:10px 10px 0;
      align-self:flex-start;
      pointer-events:none;
    }
    .camera-toolbar select {
      height:38px;
      margin:0;
      font-size:12px;
      background:#020617;
      color:#e5e7eb;
      border:1px solid var(--border);
      border-radius:8px;
      padding:0 8px;
      min-width:0;
    }
'''
    # insert after .camera-toolbar input block if exists, otherwise before @media
    pos = s.find("    @media (max-width:1100px)")
    if pos != -1:
        s = s[:pos] + css_insert + s[pos:]
    else:
        s += css_insert

# Ensure right panel display grid 60/40 in all variants
s = re.sub(r'(\.viewer-display-grid\s*\{[^}]*grid-template-columns:)\s*[^;]+;', r'\1 60fr 40fr;', s, count=1, flags=re.S)

# 2) Replace camera input with select in toolbar
s = s.replace(
    '<input id="cameraTopicInput" placeholder="/camera/color/image_raw/compressed">',
    '<select id="cameraTopicSelect"></select>'
)
s = s.replace(
    '<input id="cameraTopicInput" placeholder="/camera/color/image_raw">',
    '<select id="cameraTopicSelect"></select>'
)

# 3) DOM references: keep compatibility with old cameraTopicInput variable name
s = s.replace(
    'const cameraTopicInput=document.getElementById("cameraTopicInput");',
    'const cameraTopicSelect=document.getElementById("cameraTopicSelect");\nconst cameraTopicInput=document.getElementById("cameraTopicInput") || cameraTopicSelect;'
)

# 4) Add camera FPS state variables
if "let cameraLastRenderMs=0;" not in s:
    s = s.replace(
        'let cameraLastType="";',
        'let cameraLastType="";\nlet cameraLastRenderMs=0;\nlet cameraRawMinIntervalMs=160;\nlet cameraCompressedMinIntervalMs=60;'
    )

# 5) Replace camera helper functions from isCameraTopicType to before updateManualSliderLabels
new_camera_js = r'''function isCameraTopicType(type){
  return ["sensor_msgs/msg/CompressedImage", "sensor_msgs/msg/Image"].includes(type);
}

function isLikelyCameraTopicName(name){
  if(!name) return false;
  const n=name.toLowerCase();
  return n.includes("image") || n.includes("rgb") || n.includes("color") || n.includes("camera") || n.includes("tracker") || n.includes("alert");
}

function findCameraTopicInfo(topicName){
  if(!topicName) return null;
  return availableTopics.find(t=>t.name===topicName) || null;
}

function cameraTopicPriority(t){
  const n=(t.name || "").toLowerCase();
  const compressed=t.type==="sensor_msgs/msg/CompressedImage" ? 0 : 100;
  let p=compressed;

  if(n.includes("person_tracker")) p += 0;
  else if(n.includes("alert")) p += 2;
  else if(n.includes("color") || n.includes("rgb")) p += 5;
  else if(n.includes("depth")) p += 50;
  else p += 20;

  return p;
}

function getCameraTopicOptions(){
  return availableTopics
    .filter(t=>isCameraTopicType(t.type) && isLikelyCameraTopicName(t.name))
    .sort((a,b)=>cameraTopicPriority(a)-cameraTopicPriority(b) || a.name.localeCompare(b.name));
}

function refreshCameraTopicSelect(){
  if(!cameraTopicSelect) return;

  const oldValue=cameraTopicSelect.value;
  const opts=getCameraTopicOptions();
  cameraTopicSelect.innerHTML="";

  if(opts.length===0){
    const opt=document.createElement("option");
    opt.value="";
    opt.textContent="Không có Image topic";
    cameraTopicSelect.appendChild(opt);
    return;
  }

  opts.forEach(t=>{
    const opt=document.createElement("option");
    opt.value=t.name;
    opt.textContent=`${t.name} [${t.type.split('/').pop()}]`;
    cameraTopicSelect.appendChild(opt);
  });

  if(oldValue && opts.find(t=>t.name===oldValue)){
    cameraTopicSelect.value=oldValue;
  }
}

function autoFillCameraTopic(){
  refreshCameraTopicSelect();

  if(!cameraTopicInput) return;
  if(cameraTopicInput.value && cameraTopicInput.value.trim()) return;

  const preferred=[
    "/amr_ai/debug/person_tracker/image/compressed",
    "/amr_ai/debug/alert/image/compressed",
    "/camera/color/image_raw_web/compressed",
    "/camera/color/image_raw/compressed",
    "/camera/rgb/image_raw/compressed",
    "/camera/image_raw/compressed",
    "/amr_ai/debug/person_tracker/image",
    "/amr_ai/debug/alert/image",
    "/camera/color/image_raw",
    "/camera/rgb/image_raw",
    "/camera/image_raw"
  ];

  for(const name of preferred){
    const info=findCameraTopicInfo(name);
    if(info && isCameraTopicType(info.type)){
      cameraTopicInput.value=name;
      setCameraStatus("Camera topic tự chọn: "+name);
      return;
    }
  }

  const opts=getCameraTopicOptions();
  if(opts.length>0){
    cameraTopicInput.value=opts[0].name;
    const rawNote=opts[0].type==="sensor_msgs/msg/Image" ? ". Topic raw có thể lag, nên dùng topic compressed." : "";
    setCameraStatus("Camera topic tự chọn: "+opts[0].name+rawNote);
  }
}

function setCameraStatus(text){
  if(cameraStatus){ cameraStatus.textContent=text; }
}

function bytesToBase64(data){
  if(!data) return "";
  if(typeof data === "string") return data;

  let binary="";
  const chunkSize=0x8000;
  for(let i=0;i<data.length;i+=chunkSize){
    binary += String.fromCharCode.apply(null, data.slice(i,i+chunkSize));
  }
  return btoa(binary);
}

function bytesToUint8(data){
  if(!data) return new Uint8Array(0);
  if(typeof data === "string"){
    const bin=atob(data);
    const out=new Uint8Array(bin.length);
    for(let i=0;i<bin.length;i++) out[i]=bin.charCodeAt(i);
    return out;
  }
  return new Uint8Array(data);
}

function shouldRenderCameraFrame(isCompressed){
  const now=performance.now();
  const minInterval=isCompressed ? cameraCompressedMinIntervalMs : cameraRawMinIntervalMs;
  if(now-cameraLastRenderMs < minInterval){
    return false;
  }
  cameraLastRenderMs=now;
  return true;
}

function renderCompressedCamera(msg){
  const format=(msg.format || "jpeg").toLowerCase();
  const mime=format.includes("png") ? "image/png" : "image/jpeg";
  const b64=bytesToBase64(msg.data);

  if(cameraCanvas){ cameraCanvas.style.display="none"; }
  if(cameraImage){
    cameraImage.style.display="block";
    cameraImage.src=`data:${mime};base64,${b64}`;
  }
}

function renderRawCamera(msg){
  if(!cameraCanvas || !cameraCtx) return;

  const w=msg.width;
  const h=msg.height;
  const enc=(msg.encoding || "rgb8").toLowerCase();
  const src=bytesToUint8(msg.data);

  cameraCanvas.width=w;
  cameraCanvas.height=h;

  const img=cameraCtx.createImageData(w,h);
  const step=msg.step || (w*3);

  for(let y=0;y<h;y++){
    for(let x=0;x<w;x++){
      const dst=(y*w+x)*4;
      let r=0,g=0,b=0,a=255;

      if(enc==="rgb8"){
        const i=y*step+x*3;
        r=src[i]; g=src[i+1]; b=src[i+2];
      }else if(enc==="bgr8"){
        const i=y*step+x*3;
        b=src[i]; g=src[i+1]; r=src[i+2];
      }else if(enc==="rgba8"){
        const i=y*step+x*4;
        r=src[i]; g=src[i+1]; b=src[i+2]; a=src[i+3];
      }else if(enc==="bgra8"){
        const i=y*step+x*4;
        b=src[i]; g=src[i+1]; r=src[i+2]; a=src[i+3];
      }else if(enc==="mono8"){
        const v=src[y*step+x];
        r=v; g=v; b=v;
      }else{
        if(cameraFrameCount%30===0){
          setCameraStatus("Camera raw encoding chưa hỗ trợ: "+enc+". Nên dùng topic compressed.");
        }
        return;
      }

      img.data[dst]=r;
      img.data[dst+1]=g;
      img.data[dst+2]=b;
      img.data[dst+3]=a;
    }
  }

  if(cameraImage){ cameraImage.style.display="none"; }
  cameraCanvas.style.display="block";
  cameraCtx.putImageData(img,0,0);
}

function startCameraStream(){
  if(!ros){
    setCameraStatus("Camera: hãy CONNECT ROSBridge trước.");
    return;
  }

  refreshCameraTopicSelect();

  const topicName=(cameraTopicInput ? cameraTopicInput.value.trim() : "");
  if(!topicName){
    setCameraStatus("Camera: chưa có topic ảnh. Bấm REFRESH LIST hoặc kiểm tra node camera.");
    return;
  }

  const info=findCameraTopicInfo(topicName) || {
    name:topicName,
    type: topicName.includes("compressed") ? "sensor_msgs/msg/CompressedImage" : "sensor_msgs/msg/Image"
  };

  if(!isCameraTopicType(info.type)){
    setCameraStatus(`Camera: topic ${topicName} không phải Image/CompressedImage. Type=${info.type || "unknown"}`);
    return;
  }

  stopCameraStream(false);

  cameraLastTopic=topicName;
  cameraLastType=info.type;
  cameraFrameCount=0;
  cameraLastRenderMs=0;
  cameraActive=true;

  cameraSub=new ROSLIB.Topic({
    ros:ros,
    name:topicName,
    messageType:rosTypeToRoslibType(info.type),
    throttle_rate: info.type==="sensor_msgs/msg/CompressedImage" ? 60 : 160,
    queue_length: 1
  });

  cameraSub.subscribe((msg)=>{
    cameraFrameCount += 1;
    const isCompressed=cameraLastType==="sensor_msgs/msg/CompressedImage";
    if(!shouldRenderCameraFrame(isCompressed)) return;

    try{
      if(isCompressed) renderCompressedCamera(msg);
      else renderRawCamera(msg);

      if(cameraFrameCount===1 || cameraFrameCount%30===0){
        const typeLabel=isCompressed ? "compressed" : "raw";
        setCameraStatus(`Camera: ${cameraLastTopic} | ${typeLabel} | frame ${cameraFrameCount}`);
      }
    }catch(e){
      setCameraStatus("Camera render error: "+e);
    }
  });

  const rawNote=info.type==="sensor_msgs/msg/Image" ? " | RAW: dễ lag, nên dùng compressed" : "";
  setCameraStatus("Camera: đang subscribe "+topicName+rawNote);
  log("Camera subscribed: "+topicName+" ["+info.type+"]");
}

function stopCameraStream(updateStatus=true){
  if(cameraSub){
    try{ cameraSub.unsubscribe(); }catch(e){}
  }
  cameraSub=null;
  cameraActive=false;

  if(updateStatus){
    setCameraStatus("Camera: stopped.");
  }
}

'''

# Replace existing camera block if present. The camera block was inserted before updateManualSliderLabels.
pat = r'function isCameraTopicType\(type\)\{.*?\n\}\n\nfunction updateManualSliderLabels\(\)\{'
s2, n = re.subn(pat, new_camera_js + 'function updateManualSliderLabels(){', s, count=1, flags=re.S)
if n != 1:
    raise RuntimeError(f"Không patch được camera JS block, match={n}. File có thể chưa có camera patch cũ.")
s = s2

# 6) If refreshTopicList does not refresh camera selector after list load, ensure it does
if 'refreshCameraTopicSelect();\n  autoFillCameraTopic();' not in s:
    s = s.replace('autoFillCameraTopic();', 'refreshCameraTopicSelect();\n  autoFillCameraTopic();', 1)

TARGET.write_text(s)
print(f"Patched camera viewer v2 successfully: {TARGET}")
