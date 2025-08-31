import React, { useRef, useEffect, useState } from 'react';
import './App.css';

const App = () => {
  const canvasRef = useRef(null);
  const wsRef = useRef(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [currentColor, setCurrentColor] = useState('#000000');
  const [isConnected, setIsConnected] = useState(false);
  const [lastPosition, setLastPosition] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas.getContext('2d');
    
    // Set canvas size
    canvas.width = 800;
    canvas.height = 600;
    
    // Set drawing properties
    context.lineCap = 'round';
    context.lineJoin = 'round';
    context.lineWidth = 2;
    
    // Connect to WebSocket
    connectWebSocket();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const connectWebSocket = () => {
    try {
      wsRef.current = new WebSocket('ws://localhost:8000/ws/draw');
      
      wsRef.current.onopen = () => {
        console.log('Connected to WebSocket server');
        setIsConnected(true);
      };
      
      wsRef.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        drawLine(data.prevX, data.prevY, data.x, data.y, data.color, false);
      };
      
      wsRef.current.onclose = () => {
        console.log('Disconnected from WebSocket server');
        setIsConnected(false);
        // Attempt to reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
      };
      
      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setIsConnected(false);
      };
    } catch (error) {
      console.error('Failed to connect to WebSocket:', error);
      setIsConnected(false);
    }
  };

  const drawLine = (prevX, prevY, x, y, color, shouldBroadcast = true) => {
    const canvas = canvasRef.current;
    const context = canvas.getContext('2d');
    
    context.beginPath();
    context.moveTo(prevX, prevY);
    context.lineTo(x, y);
    context.strokeStyle = color;
    context.stroke();
    
    // Broadcast to other users if this is our own drawing
    if (shouldBroadcast && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const drawingData = {
        x,
        y,
        prevX,
        prevY,
        color
      };
      wsRef.current.send(JSON.stringify(drawingData));
    }
  };

  const startDrawing = (e) => {
    setIsDrawing(true);
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    setLastPosition({ x, y });
  };

  const draw = (e) => {
    if (!isDrawing) return;
    
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    drawLine(lastPosition.x, lastPosition.y, x, y, currentColor, true);
    setLastPosition({ x, y });
  };

  const stopDrawing = () => {
    setIsDrawing(false);
  };

  const clearCanvas = () => {
    const canvas = canvasRef.current;
    const context = canvas.getContext('2d');
    context.clearRect(0, 0, canvas.width, canvas.height);
  };

  const colors = ['#000000', '#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF', '#FFA500'];

  return (
    <div className="app">
      <header className="header">
        <h1>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2L13.09 8.26L22 9L13.09 9.74L12 16L10.91 9.74L2 9L10.91 8.26L12 2Z" fill="#3b82f6"/>
          </svg>
          Collaborative Diagramming Studio
        </h1>
        <div className="status">
          <span className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}>
            <div style={{width: '8px', height: '8px', borderRadius: '50%', backgroundColor: isConnected ? '#22c55e' : '#ef4444'}}></div>
            {isConnected ? 'Connected' : 'Offline'}
          </span>
        </div>
      </header>

      <div className="toolbar">
        <div className="toolbar-left">
          <div className="toolbar-section">
            <span className="toolbar-label">Tools</span>
            <button style={{padding: '6px 12px', border: '1px solid #d1d5db', borderRadius: '4px', background: '#3b82f6', color: 'white', fontSize: '0.8125rem'}}>
              Pen
            </button>
          </div>
          
          <div className="toolbar-section">
            <span className="toolbar-label">Colors</span>
            <div className="color-palette">
              {colors.map(color => (
                <button
                  key={color}
                  className={`color-btn ${currentColor === color ? 'active' : ''}`}
                  style={{ backgroundColor: color }}
                  onClick={() => setCurrentColor(color)}
                  title={`Select ${color}`}
                />
              ))}
            </div>
          </div>

          <div className="toolbar-section">
            <button className="clear-btn" onClick={clearCanvas}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M3 6H21M8 6V4C8 3.44772 8.44772 3 9 3H15C15.5523 3 16 3.44772 16 4V6M19 6V20C19 20.5523 18.5523 21 18 21H6C5.44772 21 5 20.5523 5 20V6H19Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              Clear
            </button>
          </div>
        </div>
      </div>

      <div className="main-content">
        <div className="canvas-container">
          <canvas
            ref={canvasRef}
            onMouseDown={startDrawing}
            onMouseMove={draw}
            onMouseUp={stopDrawing}
            onMouseLeave={stopDrawing}
            className="drawing-canvas"
          />
        </div>
      </div>

      <footer className="footer">
        <p>Professional collaborative diagramming • Real-time synchronization • Enterprise ready</p>
      </footer>
    </div>
  );
};

export default App;