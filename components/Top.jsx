import React from 'react';
import { FaSearch } from 'react-icons/fa';
import { FaUser } from 'react-icons/fa';


const Top = () => {
  return (
    <div className="top">
        <div className="top-left">
            <a href="">click AICI</a> pentru a te înscrie la newsletter.
        </div>
        <div className="top-right">
            <div className="login">
               <FaUser /> <span>login <span className="bumb">&#8226;</span>  sign up</span>
            </div>
            <div className="search">
                <input type="text" placeholder="Caută în website" />
                <FaSearch />
            </div>
        </div>
    </div>
  );
};

export default Top;
