// components/Modal.js

import React from "react";

const Modal = ({ message, onClose }) => {
  return (
    <>
      {/* Fundalul modalului */}
      <div className="fixed inset-0 bg-black opacity-50 z-40"></div>
      
      {/* Containerul modalului */}
      <div className="fixed inset-0 flex items-center justify-center z-50">
        <div className="flex items-center justify-center justify-between bg-white rounded-lg shadow-lg p-6 max-w-lg w-full relative">
          <p className="text-center text-lg mb-4">{message}</p>
          <button
            onClick={onClose}
            className="block mx-auto px-4 py-2 bg-black text-white rounded hover:bg-grey-700 transition"
          >
            OK
          </button>
        </div>
      </div>
    </>
  );
};

export default Modal;
