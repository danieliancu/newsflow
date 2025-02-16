import React from 'react';
import { FaUser } from 'react-icons/fa';

const Top = ({ 
  searchTerm, 
  setSearchTerm, 
  setIsSearching, 
  setSubmittedSearchTerm 
}) => {

  const handleChange = (e) => {
    setSearchTerm(e.target.value);
  };

  const handleSearch = () => {
    if (searchTerm.trim().length > 0) {
      setSubmittedSearchTerm(searchTerm);
      setIsSearching(true);
      window.scrollTo({ top: 0, behavior: "smooth" });
      console.log("Submitted searchTerm:", searchTerm);
    } else {
      setSubmittedSearchTerm("");
      setIsSearching(false);
    }
  };

  const handleClear = () => {
    setSearchTerm("");
    setSubmittedSearchTerm("");
    setIsSearching(false);
  };

  return (
    <div className="top">
      <div className="top-left">
        <a href="#footer">click AICI</a> pentru a te înscrie la newsletter.
      </div>

      <div className="top-right">
        <div className="login-container">
          <FaUser />{" "}
          <span>
            login <span className="bumb">&#8226;</span> sign up
          </span>
        </div>

        <div className="search" style={{ position: "relative" }}>
          <input
            type="text"
            placeholder="Caută în website"
            value={searchTerm}
            onChange={handleChange}
          />

          {searchTerm.length > 0 && (
            <svg
              onClick={handleClear}
              style={{
                cursor: "pointer",
                marginLeft: 5,
                position: "absolute",
                right: "2.5em",
                top: "50%",
                transform: "translateY(-50%)",
                fill: "black",
                background: "transparent",
                height: "30px"
              }}
              xmlns="http://www.w3.org/2000/svg"
              fill="currentColor"
              width="1em"
              height="1em"
              viewBox="0 0 352 512"
            >
              <path d="M242.72 256l100.07-100.07a23.999 23.999 0 10-33.94-33.94L208.78 
              222.06 108.72 122a23.999 23.999 0 10-33.94 33.94L174.84 256 
              74.78 356.07a23.999 23.999 0 1033.94 33.94l100.06-100.07 
              100.07 100.07a23.999 23.999 0 0033.94 0l28.3-28.3c9.4-9.4 
              9.4-24.6.1-34z"/>
            </svg>
          )}

          <svg
            onClick={handleSearch}
            style={{
              cursor: "pointer",
              marginLeft: 5,
              position: "absolute",
              right: "0em",
              top: "50%",
              transform: "translateY(-50%)"
            }}
            stroke="currentColor"
            fill="currentColor"
            strokeWidth="0"
            viewBox="0 0 512 512"
            height="1em"
            width="1em"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path d="M505 442.7L405.3 343c-4.5-4.5-10.6-7-17-7H372c27.6-35.3 
            44-79.7 44-128C416 93.1 322.9 0 208 0S0 93.1 0 
            208s93.1 208 208 208c48.3 0 92.7-16.4 
            128-44v16.3c0 6.4 2.5 12.5 7 
            17l99.7 99.7c9.4 9.4 24.6 9.4 
            33.9 0l28.3-28.3c9.4-9.4 
            9.4-24.6.1-34zM208 336c-70.7 
            0-128-57.2-128-128 0-70.7 
            57.2-128 128-128 70.7 
            0 128 57.2 128 128 
            0 70.7-57.2 
            128-128 128z"/>
          </svg>
        </div>
      </div>
    </div>
  );
};

export default Top;
