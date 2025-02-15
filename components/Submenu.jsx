import React from 'react';
import { FaFilter } from 'react-icons/fa';

const SubMenu = ({ selectedSort, onSortChange }) => {
  return (
    <div className="containerSubMenu">
      <div className="filter">
        <FaFilter style={{ fontSize:"16px", display: "inline", verticalAlign: "sub", paddingRight: "2px" }} />
        Filter
      </div>
      <div className="sort">
        <select value={selectedSort} onChange={(e) => onSortChange(e.target.value)}>
          <option value="Cele mai noi">Cele mai noi</option>
          <option value="Cele mai vechi">Cele mai vechi</option>            
          <option value="Alfabetic A-Z">Alfabetic A-Z</option>            
          <option value="Alfabetic Z-A">Alfabetic Z-A</option>
        </select>
      </div>
    </div>
  );
};

export default SubMenu;
