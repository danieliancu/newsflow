import React, {useState} from "react";
import Slider from "react-slick";
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
        breakpoint: 600, // La ecrane cu lățimea mai mică de 600px
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
          {items.map((item, index) => (
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
                  <div class="supra">{item.source}</div>
                  <a
                    href={item.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ textDecoration: "none", color: "white" }}
                  >
                    <h3 style={{ margin: "5px 0" }}>{item.text}</h3>
                    <p className="ago" style={{ color:"white", fontSize:"12px" }}>
                    <TimeAgo date={item.date} source={item.source} selectedSource={selectedSource} />
                    </p>
                  </a>
                </div>
              </div>
            </div>
          ))}
        </Slider>


    </div>
  );
};

export default React.memo(Carousel, (prevProps, nextProps) => {
  return JSON.stringify(prevProps.items) === JSON.stringify(nextProps.items);
});
