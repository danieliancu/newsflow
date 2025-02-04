import React from "react";
import Slider from "react-slick";
import "slick-carousel/slick/slick.css";
import "slick-carousel/slick/slick-theme.css";

const Carousel = ({ items }) => {
  const carouselSettings = {
    dots: true,
    infinite: true,
    speed: 500,
    slidesToShow: 3,
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
                      {(() => {
                          const now = new Date();
                          const date = new Date(item.date);
                          const diffMs = now - date;
                          const diffMinutes = Math.floor(diffMs / 60000);
                          if (diffMinutes === 0) {
                            return `Chiar acum`;
                          } else if (diffMinutes === 1) {
                            return `Acum 1 minut`;
                          } else if (diffMinutes < 60) {
                            return diffMinutes > 19
                              ? `Acum ${diffMinutes} de minute`
                              : `Acum ${diffMinutes} minute`;
                          } else {
                            const hours = Math.floor(diffMinutes / 60);
                            const minutes = diffMinutes % 60;
                            const hourText =
                              hours === 1
                                ? "o oră"
                                : hours === 2
                                ? "două ore"
                                : `${hours} ore`;
                            const minuteText =
                              minutes === 0
                                ? ""
                                : minutes > 19
                                ? `${minutes} de minute`
                                : `${minutes} minute`;
                            return `Acum ${hourText}${minuteText ? ` și ${minuteText}` : ""}`;
                          }
                        })()}
                        <span className="bumb">&#8226;</span>
                        <strong className="news-source" style={{ padding:"0" }}>{item.source}</strong>
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
