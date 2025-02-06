import React from 'react';
import { FaSearch, FaUser } from 'react-icons/fa';

const Top = () => {
  return (
    <div className="top">
      <div className="top-left">
        <a href="#footer">click AICI</a> pentru a te înscrie la newsletter.
      </div>
      <div className="top-right">
        <div className="login-container">
          <FaUser /> <span>login <span className="bumb">&#8226;</span>  sign up</span>
        </div>
        {/* Acest div .search îl vom anima cu CSS când body are clasa "search-open" */}
        <div className="search">
          <input type="text" placeholder="Caută în website" />
          <FaSearch />
        </div>
      </div>
    </div>
  );
};

export default Top;
