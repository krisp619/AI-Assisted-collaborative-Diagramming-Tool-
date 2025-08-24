import { useEffect, useRef } from "react";

function App() {
  const canvasRef = useRef(null);
  const socketRef = useRef(null);

  useEffect(() => {
    // Backend WebSocket ला connect करा (backend तुझ्या मित्राकडे चालू असायला हवं)
    socketRef.current = new WebSocket("ws://localhost:8000/ws/draw");

    socketRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const ctx = canvasRef.current.getContext("2d");
      ctx.strokeStyle = data.color || "black";
      ctx.beginPath();
      ctx.moveTo(data.prevX, data.prevY);
      ctx.lineTo(data.x, data.y);
      ctx.stroke();
    };
  }, []);

  const handleDraw = (e) => {
    const ctx = canvasRef.current.getContext("2d");
    const x = e.nativeEvent.offsetX;
    const y = e.nativeEvent.offsetY;

    ctx.lineTo(x, y);
    ctx.stroke();

    socketRef.current.send(
      JSON.stringify({ x, y, prevX: x - 1, prevY: y - 1, color: "black" })
    );
  };

  return (
    <div>
      <h2>Collaborative Whiteboard</h2>
      <canvas
        ref={canvasRef}
        width={800}
        height={600}
        style={{ border: "1px solid black" }}
        onMouseMove={(e) => {
          if (e.buttons === 1) handleDraw(e);
        }}
      />
    </div>
  );
}

export default App;

