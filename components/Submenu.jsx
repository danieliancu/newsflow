import React, { useRef, useEffect } from 'react';
import { FaFilter, FaTimes } from 'react-icons/fa';
import { useDragScroll } from './hooks/useDragScroll';


const overlayStyle = {
  position: 'fixed',
  top: 0,
  left: 0,
  width: '100%',
  height: '100%',
  backgroundColor: 'rgba(0,0,0,0.4)',
  zIndex: 900,
};

const panelStyle = {
  position: 'fixed',
  left: 0,
  top: 0,
  maxWidth: '450px',
  width: '100%',
  height: '100%',
  backgroundColor: '#fff',
  boxShadow: '2px 0 5px rgba(0,0,0,0.3)',
  zIndex: 1000,
  padding: '20px',
  overflowY: 'auto',
  transition: 'transform 0.3s ease-in-out',
};

const Submenu = ({
  selectedSort,
  onSortChange,
  availableSources,
  availableLabels,
  isPanelOpen,
  openPanel,
  closePanel,
  submenuSourceFilters,
  onSourceFilterChange,
  submenuLabelFilters,
  onLabelFilterChange,
  onResetFilters,
}) => {
  // Sortează sursele și etichetele fără a modifica array-ul original
  const sortedSources = availableSources.slice().sort((a, b) =>
    a.localeCompare(b)
  );
  const sortedLabels = availableLabels.slice().sort((a, b) =>
    a.localeCompare(b)
  );

  const hasActiveFilters =
    submenuSourceFilters.length > 0 || submenuLabelFilters.length > 0;
  const showResetButton = hasActiveFilters;

  // Referința pentru elementul ce va avea drag & scroll
  const sliderRef = useRef(null);
  useDragScroll(sliderRef);

  return (
    <div className="containerDisplayFilter">
      <div
        style={{ display: hasActiveFilters ? 'block' : 'none' }}      
        className="displayFilter-faded"
      >
        
      </div>
      <div
        ref={sliderRef}
        className="displayFilter"
        style={{ display: hasActiveFilters ? 'flex' : 'none' }}
      >
        {hasActiveFilters && <div style={{ padding: '4px 0' }}>Arată doar:</div>}
        {submenuSourceFilters.map((source, index) => (
          <div className="displayFilterElement" key={`source-${index}`}>
            <span>{source}</span>
            <FaTimes
              className="x"
              onClick={() =>
                onSourceFilterChange(
                  submenuSourceFilters.filter((item) => item !== source)
                )
              }
            />
          </div>
        ))}
        {submenuLabelFilters.map((label, index) => (
          <div
            className="displayFilterElement"
            key={`label-${index}`}
            style={{
              display: 'flex',
              alignItems: 'center',
              background: '#eee',
              padding: '4px 8px',
              borderRadius: '4px',
            }}
          >
            <span>{label}</span>
            <FaTimes
              style={{
                marginLeft: '4px',
                cursor: 'pointer',
                color: 'red',
              }}
              onClick={() =>
                onLabelFilterChange(
                  submenuLabelFilters.filter((item) => item !== label)
                )
              }
            />
          </div>
        ))}
      </div>

      <div className="containerSubMenu">
        <div
          className="filter"
          style={{ cursor: 'pointer', display: 'flex', alignItems: 'center' }}
          onClick={openPanel}
        >
          <FaFilter
            style={{
              fontSize: '16px',
              display: 'inline',
              verticalAlign: 'sub',
              paddingRight: '2px',
            }}
          />
          Filtrează știrile
        </div>

        <div className="sort">
          <select
            value={selectedSort}
            onChange={(e) => onSortChange(e.target.value)}
          >
            <option value="Cele mai noi">Cele mai noi</option>
            <option value="Cele mai vechi">Cele mai vechi</option>
            <option value="Alfabetic A-Z">Alfabetic A-Z</option>
            <option value="Alfabetic Z-A">Alfabetic Z-A</option>
          </select>
        </div>
      </div>

      {isPanelOpen && (
        <>
          <div style={overlayStyle} onClick={closePanel} />
          <div
            className="filter-panel"
            style={{
              ...panelStyle,
              transform: isPanelOpen ? 'translateX(0)' : 'translateX(-100%)',
            }}
          >
            <div
              className="panel-header"
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '20px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <h3 style={{ padding: '5px 0' }}>Filtre</h3>
                {showResetButton && (
                  <button
                    onClick={() => {
                      onResetFilters();
                    }}
                    style={{
                      padding: '4px 8px',
                      borderRadius: '4px',
                      border: '1px solid red',
                      background: 'white',
                      color: 'red',
                      cursor: 'pointer',
                    }}
                  >
                    Dezactivează toate filtrele
                  </button>
                )}
              </div>
              <FaTimes
                style={{ cursor: 'pointer', fontSize: '20px' }}
                onClick={closePanel}
              />
            </div>
            <div className="panel-content" style={{ display: 'flex' }}>
              <div className="sources" style={{ flex: 1, paddingRight: '10px' }}>
                <h4>Sursă știri</h4>
                <ul style={{ listStyle: 'none', padding: 0 }}>
                  {sortedSources.map((source, index) => (
                    <li key={index} style={{ marginBottom: '4px' }}>
                      <label
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          fontSize: '14px',
                        }}
                      >
                        <input
                          type="checkbox"
                          className="custom-checkbox"
                          checked={submenuSourceFilters.includes(source)}
                          onChange={() => {
                            if (submenuSourceFilters.includes(source)) {
                              onSourceFilterChange(
                                submenuSourceFilters.filter((item) => item !== source)
                              );
                            } else {
                              onSourceFilterChange([...submenuSourceFilters, source]);
                            }
                          }}
                        />
                        {source}
                      </label>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="labels" style={{ flex: 1, paddingLeft: '10px' }}>
                <h4>Etichete</h4>
                <ul style={{ listStyle: 'none', padding: 0 }}>
                  {sortedLabels.map((label, index) => (
                    <li key={index} style={{ marginBottom: '4px' }}>
                      <label
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          fontSize: '14px',
                        }}
                      >
                        <input
                          type="checkbox"
                          className="custom-checkbox"
                          checked={submenuLabelFilters.includes(label)}
                          onChange={() => {
                            if (submenuLabelFilters.includes(label)) {
                              onLabelFilterChange(
                                submenuLabelFilters.filter((item) => item !== label)
                              );
                            } else {
                              onLabelFilterChange([...submenuLabelFilters, label]);
                            }
                          }}
                        />
                        {label}
                      </label>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default Submenu;
