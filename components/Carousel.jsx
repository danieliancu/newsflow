import React, { useState } from "react";
import Slider from "react-slick";
import Link from "next/link";
import "slick-carousel/slick/slick.css";
import "slick-carousel/slick/slick-theme.css";
import TimeAgo from "./TimeAgo";

const Carousel = ({ items }) => {
  const [selectedSource, setSelectedSource] = useState("all");

  const carouselSettings = {
    dots: false,
    infinite: true,
    speed: 500,
    slidesToShow: 1,
    slidesToScroll: 1,
    arrows: true,
    autoplay: true,
    autoplaySpeed: 5000,
    responsive: [
      {
        breakpoint: 600, // Pentru ecrane cu lățime mai mică de 600px
        settings: {
          slidesToShow: 1,
          slidesToScroll: 1,
        },
      },
    ],
  };

  return (
    <div className="container-all-carousel">
      <Slider {...carouselSettings}>
        {items.map((item, index) => {
          const slug =
            item.text
              ?.toLowerCase()
              .replace(/[^a-z0-9]+/g, "-")
              .replace(/^-|-$/g, "") || "stire";
          return (
            <div key={index}>
              <div className="slick-art">
                <img
                  src={item.imgSrc}
                  alt={item.text || "Image"}
                  style={{
                    width: "100%",
                    height: "100%",
                    objectFit: "cover",
                    display: "block",
                  }}
                />
                <div className="degrade">
                  <p className="supra-desktop">{item.label}</p>
                  <div className="supra">
                    <TimeAgo
                      date={item.date}
                      source={item.source}
                      selectedSource={selectedSource}
                    />
                  </div>
                  <Link href={`/news/${slug}-${item.id}`}>
                    {/* Înlocuim <a> cu un container ce permite stilizare și navigare */}
                    <div style={{ textDecoration: "none", color: "white", cursor: "pointer" }}>
                      <h3 style={{ margin: "5px 0" }}>{item.text}</h3>
                      <p className="ago" style={{ color: "white", fontSize: "12px" }}>
                        <TimeAgo
                          date={item.date}
                          source={item.source}
                          selectedSource={selectedSource}
                        />
                      </p>
                    </div>
                  </Link>
                </div>
              </div>
            </div>
          );
        })}
      </Slider>
    </div>
  );
};

export default React.memo(Carousel, (prevProps, nextProps) => {
  return JSON.stringify(prevProps.items) === JSON.stringify(nextProps.items);
});
