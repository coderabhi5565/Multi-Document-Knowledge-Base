import React from "react";
import "./DocumentsSection.css";

export default function DocumentsSection({ documents }) {
  return (
    <section className="documents-section">
      <h2>Documents in Knowledge Base</h2>
      <table className="documents-table">
        <thead>
          <tr>
            <th>Filename / URL</th>
            <th>Type</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {documents.map((doc, idx) => (
            <tr key={idx}>
              <td>{doc.name}</td>
              <td>{doc.type}</td>
              <td>{doc.status}</td>
              <td className="remove-cell">
                <button className="remove-btn" aria-label="Remove" title="Remove" disabled>
                  ✕
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
