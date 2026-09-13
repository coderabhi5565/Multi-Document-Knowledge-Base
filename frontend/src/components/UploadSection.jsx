import React, { useState } from "react";
import "./UploadSection.css";

export default function UploadSection() {
  const [url, setUrl] = useState("");

  const handleAddUrl = () => {
    if (url.trim()) {
      // Placeholder: In a real app we would add the URL to the document list
      console.log("Add URL:", url);
      setUrl("");
    }
  };

  const handleFilesSelected = (e) => {
    const files = e.target.files;
    console.log("Selected files:", files);
    // Placeholder: In a real app we would add the files to the document list
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const files = e.dataTransfer.files;
    console.log("Dropped files:", files);
    // Placeholder for drop handling
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  return (
    <section className="upload-section">
      <h2>Ingest Documents</h2>
      <div
        className="drag-drop"
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onClick={() => document.getElementById('file-input').click()}
      >
        Drag & drop files here, or click to select (PDF, DOCX, TXT)
        <input
          id="file-input"
          type="file"
          multiple
          accept=".pdf,.docx,.txt"
          style={{ display: "none" }}
          onChange={handleFilesSelected}
        />
      </div>
      <div className="url-input">
        <input
          type="text"
          placeholder="Enter a web page URL"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
        />
        <button type="button" onClick={handleAddUrl}>
          Add URL
        </button>
      </div>
    </section>
  );
}
