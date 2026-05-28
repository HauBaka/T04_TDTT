<div align="center">

<h1>Lodgy4U</h1>

<p><strong>Nền tảng tìm kiếm & gợi ý lưu trú thông minh, hỗ trợ bởi AI</strong></p>

<br/>

<a href="https://github.com/HauBaka/T04_TDTT"><img src="https://img.shields.io/badge/Backend%20Repo-181717?style=for-the-badge&logo=github&logoColor=white" /></a>
<a href="https://github.com/KhoaTapCode2006/FE_TDTT_REACT"><img src="https://img.shields.io/badge/Frontend%20Repo-181717?style=for-the-badge&logo=github&logoColor=white" /></a>
<a href="#hướng-dẫn-cài-đặt"><img src="https://img.shields.io/badge/Bắt%20đầu%20ngay-22c55e?style=for-the-badge&logo=rocket&logoColor=white" /></a>

<br/><br/>

<img src="https://img.shields.io/badge/Loại%20dự%20án-AI%20%2F%20Fullstack-6366f1?style=flat-square" />
<img src="https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" />
<img src="https://img.shields.io/badge/AI-Gemini%20%2B%20PhoBERT-4285F4?style=flat-square&logo=google&logoColor=white" />
<img src="https://img.shields.io/badge/Database-Firestore-FFCA28?style=flat-square&logo=firebase&logoColor=black" />
<img src="https://img.shields.io/badge/Cache-Redis-DC382D?style=flat-square&logo=redis&logoColor=white" />
<img src="https://img.shields.io/badge/Storage-Cloudflare%20R2-F38020?style=flat-square&logo=cloudflare&logoColor=white" />
<img src="https://img.shields.io/badge/Trạng%20thái-Đang%20phát%20triển-22c55e?style=flat-square" />

<br/><br/>

> **Lodgy4U** giúp người dùng thoát khỏi tình trạng quá tải thông tin khi tìm khách sạn — bằng cách kết hợp tìm kiếm đa nguồn, xếp hạng đa tín hiệu và chatbot AI hiểu ngôn ngữ tự nhiên.

</div>

---

## Giới thiệu

> [!NOTE]
> Hệ thống hỗ trợ tìm kiếm và lên lịch trình du lịch thông minh, giúp giải quyết tình trạng quá tải thông tin và hỗ trợ người dùng đưa ra quyết định lưu trú tối ưu nhất.

Dự án kết hợp giữa công nghệ xử lý ngôn ngữ tự nhiên và kiến trúc backend phân tán để mang lại trải nghiệm tìm kiếm tự nhiên, cá nhân hóa theo từng nhu cầu thực tế của người dùng thông qua các thành phần cấu trúc sau:

<table width="100%" style="border-collapse: collapse; margin-top: 15px;">
  <tr>
    <td style="padding: 12px 15px; border-left: 4px solid #58a6ff; background-color: #161b22; border-radius: 0 6px 6px 0; margin-bottom: 10px; display: block;">
      <strong>Hợp nhất Dữ liệu Thời gian thực:</strong> Tự động thu thập, sàng lọc và đồng bộ thông tin giá phòng, tình trạng phòng trống từ nguồn nội bộ (<code>Firestore</code>) và dịch vụ bên ngoài (<code>SerpAPI</code>).
    </td>
  </tr>
  <tr>
    <td style="padding: 12px 15px; border-left: 4px solid #34a853; background-color: #161b22; border-radius: 0 6px 6px 0; margin-bottom: 10px; display: block;">
      <strong>Trợ lý AI Hiểu Ngữ cảnh:</strong> Chatbot thông minh tự động phân loại ý định người dùng, đưa ra gợi ý lưu trú chính xác kèm theo giải thích minh bạch để tối ưu hóa lựa chọn.
    </td>
  </tr>
  <tr>
    <td style="padding: 12px 15px; border-left: 4px solid #ffca28; background-color: #161b22; border-radius: 0 6px 6px 0; margin-bottom: 10px; display: block;">
      <strong>Hiệu chỉnh Đánh giá Khách quan:</strong> Ứng dụng mô hình <code>PhoBERT</code> để phân tích cảm xúc các bài đánh giá, tự động phát hiện và hạ trọng số tin cậy của các lượt reviews ảo hoặc spam.
    </td>
  </tr>
  <tr>
    <td style="padding: 12px 15px; border-left: 4px solid #ff7b72; background-color: #161b22; border-radius: 0 6px 6px 0; margin-bottom: 10px; display: block;">
      <strong>Định vị Không gian Chính xác:</strong> Áp dụng thuật toán <code>Geohash</code> và công thức <code>Haversine</code> để tìm kiếm vị trí địa lý thực tế và tính khoảng cách chính xác từ người dùng đến điểm đến.
    </td>
  </tr>
  <tr>
    <td style="padding: 12px 15px; border-left: 4px solid #79c0ff; background-color: #161b22; border-radius: 0 6px 6px 0; margin-bottom: 0; display: block;">
      <strong>Tối ưu Tốc độ Hệ thống:</strong> Giảm tải độ trễ cho ứng dụng thông qua pipeline xử lý bất đồng bộ, bộ nhớ đệm <code>Redis</code> và các tác vụ tính toán AI chạy ngầm dưới nền (<code>Background Workers</code>).
    </td>
  </tr>
</table>

---

## Tính năng chính

<table width="100%" style="border-collapse: separate; border-spacing: 15px; max-width: 100%;">
  
  <tr>
    <td width="50%" valign="top" style="padding: 16px; border: 1px solid #30363d; border-radius: 8px; background-color: #0d1117;">
      <h3 style="margin-top: 0; color: #58a6ff;">💬 Trợ lý Du lịch Thông minh</h3>
      <p style="color: #8b949e; font-size: 13.5px; margin-bottom: 0; line-height: 1.6; text-align: justify;">
        Tích hợp Chatbot giúp người dùng tìm kiếm và lên lịch trình tự nhiên như đang trò chuyện. Hệ thống tự động phân tích nhu cầu, ngân sách và gợi ý các điểm lưu trú phù hợp nhất thay vì phải tự lọc thủ công.
      </p>
    </td>
    <td width="50%" valign="top" style="padding: 16px; border: 1px solid #30363d; border-radius: 8px; background-color: #0d1117;">
      <h3 style="margin-top: 0; color: #58a6ff;">⭐ Xếp hạng Cá nhân hóa</h3>
      <p style="color: #8b949e; font-size: 13.5px; margin-bottom: 0; line-height: 1.6; text-align: justify;">
        Không chỉ dựa vào số sao đánh giá, hệ thống sắp xếp khách sạn theo đúng nhu cầu người dùng. Các yếu tố như phong cách du lịch, thời tiết thực tế và lịch sử tìm kiếm đều được tính toán để đưa ra kết quả tốt nhất.
      </p>
    </td>
  </tr>

  <tr>
    <td width="50%" valign="top" style="padding: 16px; border: 1px solid #30363d; border-radius: 8px; background-color: #0d1117;">
      <h3 style="margin-top: 0; color: #58a6ff;">🤝 Quản lý Nhóm & Cộng tác</h3>
      <p style="color: #8b949e; font-size: 13.5px; margin-bottom: 0; line-height: 1.6; text-align: justify;">
        Cung cấp không gian làm việc chung để nhóm bạn bè cùng lên kế hoạch, theo dõi lộ trình của nhau để đảm bảo an toàn. Mọi người có thể lưu chung các khách sạn yêu thích vào bộ sưu tập, gửi lời mời và nhận thông báo.
      </p>
    </td>
    <td width="50%" valign="top" style="padding: 16px; border: 1px solid #30363d; border-radius: 8px; background-color: #0d1117;">
      <h3 style="margin-top: 0; color: #58a6ff;">⚡ Tối ưu Tốc độ Phản hồi</h3>
      <p style="color: #8b949e; font-size: 13.5px; margin-bottom: 0; line-height: 1.6; text-align: justify;">
        Giảm tải cho hệ thống bằng cách tách các tác vụ nặng (như tóm tắt reviews, phân tích cảm xúc) xuống xử lý ngầm dưới nền. Kết hợp đồng bộ dữ liệu phòng từ SerpAPI và bộ nhớ đệm để hạn chế tối đa độ trễ khi gọi API.
      </p>
    </td>
  </tr>

</table>

---

## Công nghệ sử dụng

<table width="100%">
  <tr>
    <td width="50%" valign="top" style="padding: 15px; border: 1px solid #30363d; border-radius: 6px;">
      <h3><a href="#" style="text-decoration: none; color: #58a6ff;">Backend Services</a></h3>
      <p style="color: #8b949e; font-size: 14px; min-height: 80px;">
        Hệ thống API cốt lõi được xây dựng trên nền tảng bất đồng bộ, xử lý toàn bộ các luồng REST API, routing, xác thực người dùng chặt chẽ qua token và kiểm thử/validate dữ liệu đầu vào nghiêm ngặt đảm bảo hiệu năng cao.
      </p>
      <br />
      <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" /></a>
      <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" /></a>
      <a href="https://uvicorn.dev"><img src="https://img.shields.io/badge/Uvicorn-ASGI-464646?style=flat-square" /></a>
      <a href="https://docs.pydantic.dev/"><img src="https://img.shields.io/badge/Pydantic-E92063?style=flat-square&logo=pydantic&logoColor=white" /></a>
      <a href="https://pyjwt.readthedocs.io/"><img src="https://img.shields.io/badge/JWT-000000?style=flat-square&logo=jsonwebtokens&logoColor=white" /></a>
    </td>
    <td width="50%" valign="top" style="padding: 15px; border: 1px solid #30363d; border-radius: 6px;">
      <h3><a href="#" style="text-decoration: none; color: #58a6ff;">AI / ML Pipeline</a></h3>
      <p style="color: #8b949e; font-size: 14px; min-height: 80px;">
        Pipeline xử lý ngôn ngữ tự nhiên thông minh kết hợp giữa các mô hình ngôn ngữ lớn (LLM) tốc độ cao, tác vụ phân tích cảm xúc tiếng Việt chuyên sâu và khả năng tự vận hành offline giúp tối ưu hóa chi phí API vận hành.
      </p>
      <br />
      <a href="https://deepmind.google/technologies/gemini/"><img src="https://img.shields.io/badge/Google%20Gemini-4285F4?style=flat-square&logo=google&logoColor=white" /></a>
      <a href="https://huggingface.co/vinai/phobert-base"><img src="https://img.shields.io/badge/PhoBERT-FFD21E?style=flat-square&logo=huggingface&logoColor=black" /></a>
      <a href="https://groq.com/"><img src="https://img.shields.io/badge/Groq-F55036?style=flat-square" /></a>
      <a href="https://ollama.com/"><img src="https://img.shields.io/badge/Ollama-black?style=flat-square" /></a>
      <a href="https://pytorch.org/"><img src="https://img.shields.io/badge/PyTorch-EE4C2C?style=flat-square&logo=pytorch&logoColor=white" /></a>
      <a href="https://huggingface.co/docs/transformers/"><img src="https://img.shields.io/badge/Transformers-FFD21E?style=flat-square&logo=huggingface&logoColor=black" /></a>
    </td>
  </tr>
  
  <tr>
    <td width="50%" valign="top" style="padding: 15px; border: 1px solid #30363d; border-radius: 6px;">
      <h3><a href="#" style="text-decoration: none; color: #58a6ff;">Database & Storage</a></h3>
      <p style="color: #8b949e; font-size: 14px; min-height: 80px;">
        Lưu trữ dữ liệu phân tán linh hoạt kết hợp giữa cơ sở dữ liệu tài liệu thời gian thực, lớp bộ nhớ đệm (cache) hiệu năng cao giúp giảm tải API và giải pháp lưu trữ tệp tin đám mây bảo mật qua presigned URL.
      </p>
      <br />
      <a href="https://firebase.google.com/docs/firestore"><img src="https://img.shields.io/badge/Firestore-FFCA28?style=flat-square&logo=firebase&logoColor=black" /></a>
      <a href="https://redis.io/"><img src="https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white" /></a>
      <a href="https://developers.cloudflare.com/r2/"><img src="https://img.shields.io/badge/Cloudflare%20R2-F38020?style=flat-square&logo=cloudflare&logoColor=white" /></a>
    </td>
    <td width="50%" valign="top" style="padding: 15px; border: 1px solid #30363d; border-radius: 6px;">
      <h3><a href="#" style="text-decoration: none; color: #58a6ff;">External Services</a></h3>
      <p style="color: #8b949e; font-size: 14px; min-height: 80px;">
        Tích hợp các dịch vụ bên thứ ba mở rộng giúp thu thập dữ liệu khách sạn thực tế, định vị tọa độ địa lý (Geocoding) chính xác tại Việt Nam, cập nhật thời tiết thời gian thực và quản lý định danh người dùng tập trung.
      </p>
      <br />
      <a href="https://serpapi.com/"><img src="https://img.shields.io/badge/SerpAPI-34A853?style=flat-square" /></a>
      <a href="https://maps.vietmap.vn/"><img src="https://img.shields.io/badge/VietMap-1a73e8?style=flat-square&logo=googlemaps&logoColor=white" /></a>
      <a href="https://open-meteo.com/"><img src="https://img.shields.io/badge/Open--Meteo-0EA5E9?style=flat-square" /></a>
      <a href="https://firebase.google.com/docs/auth"><img src="https://img.shields.io/badge/Firebase%20Auth-FFCA28?style=flat-square&logo=firebase&logoColor=black" /></a>
    </td>
  </tr>
</table>

---

## Cấu trúc thư mục

📂 **[T04_TDTT](.)/**

<details>
<summary>📁 <code>api</code>/ — <em>Chứa các router và các endpoint định tuyến HTTP requests</em></summary>

- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`auth.py`](api/auth.py) — *API xác thực người dùng, đăng ký, đăng nhập và xử lý token*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`chatbot.py`](api/chatbot.py) — *API xử lý hội thoại và tương tác với chatbot AI*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`collection.py`](api/collection.py) — *API quản lý bộ sưu tập địa điểm và khách sạn*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`conversation.py`](api/conversation.py) — *API quản lý và truy xuất lịch sử hội thoại*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`discover.py`](api/discover.py) — *API xử lý luồng khám phá và gợi ý du lịch*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`health.py`](api/health.py) — *API kiểm tra trạng thái hoạt động của hệ thống (Healthcheck)*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`hotel.py`](api/hotel.py) — *API truy xuất thông tin chi tiết và danh sách khách sạn*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`invitation.py`](api/invitation.py) — *API gửi, nhận và phê duyệt lời mời cộng tác nhóm*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`notification.py`](api/notification.py) — *API quản lý và đẩy thông báo tới người dùng*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`trip.py`](api/trip.py) — *API khởi tạo và quản lý lịch trình chuyến đi*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`upload.py`](api/upload.py) — *API xử lý tải lên tệp tin và hình ảnh lên Cloudflare R2*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`user.py`](api/user.py) — *API cập nhật và quản lý thông tin hồ sơ cá nhân*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`user_travel_preference.py`](api/user_travel_preference.py) — *API thiết lập sở thích và phong cách du lịch của user*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`view.py`](api/view.py) — *API ghi nhận lượt tương tác, lượt xem cấu trúc dữ liệu*

</details>

<details>
<summary>📁 <code>core</code>/ — <em>Cấu hình hệ thống lõi, kết nối cơ sở dữ liệu và bảo mật</em></summary>

- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`cache.py`](core/cache.py) — *Khởi tạo và cấu hình bộ nhớ đệm Redis cache*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`database.py`](core/database.py) — *Thiết lập kết nối với Firestore và các cấu hình DB chính*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`dependencies.py`](core/dependencies.py) — *Khai báo các tầng phụ thuộc (Dependency Injection) cho FastAPI*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`exceptions.py`](core/exceptions.py) — *Định nghĩa và xử lý tập trung lỗi hệ thống (Global Error Exception)*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`http_client.py`](core/http_client.py) — *Client bất đồng bộ cấu hình sẵn để gọi các dịch vụ bên ngoài*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`limiter.py`](core/limiter.py) — *Cấu hình Rate Limiting ngăn chặn spam requests*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`settings.py`](core/settings.py) — *Quản lý biến môi trường và thiết lập chung của ứng dụng*

</details>

<details>
<summary>📁 <code>externals</code>/ — <em>Tích hợp mô hình AI và dịch vụ API bên thứ ba</em></summary>

- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`Gemini.py`](externals/Gemini.py) — *Tích hợp và gọi API Google Gemini xử lý sinh nội dung*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`GroqLLM.py`](externals/GroqLLM.py) — *Tích hợp mô hình LLM qua Groq xử lý router ý định hội thoại*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`OllamaSummary.py`](externals/OllamaSummary.py) — *Kết nối LLM cục bộ qua Ollama hỗ trợ tác vụ tóm tắt*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`PhoBERT.py`](externals/PhoBERT.py) — *Inference mô hình PhoBERT xử lý NLP tiếng Việt*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`SemanticModel.py`](externals/SemanticModel.py) — *Mô hình xử lý nhúng vector (embedding) phục vụ tìm kiếm ngữ nghĩa*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`SerpAPI.py`](externals/SerpAPI.py) — *Tích hợp SerpAPI để cào dữ liệu Google Hotels theo thời gian thực*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`VietMapAPI.py`](externals/VietMapAPI.py) — *Kết nối dịch vụ VietMap hỗ trợ Geocoding địa chỉ Việt Nam*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`WeatherOpenMeteo.py`](externals/WeatherOpenMeteo.py) — *Lấy thông tin thời tiết điểm đến từ Open-Meteo*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`r2_client.py`](externals/r2_client.py) — *Cấu hình S3 Client kết nối và truyền tải ảnh lên Cloudflare R2*

</details>

<details>
<summary>📁 <code>mock_data</code>/ — <em>Dữ liệu giả lập dùng cho quá trình thử nghiệm và kiểm thử</em></summary>

- 📊 `user_reviews.csv` — *File dữ liệu CSV chứa các bình luận mẫu của người dùng phục vụ phân tích cảm xúc*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`virtual_review.py`](mock_data/virtual_review.py) — *Script sinh và giả lập dữ liệu đánh giá hệ thống*

</details>

<details>
<summary>📁 <code>repositories</code>/ — <em>Tầng làm việc trực tiếp với cơ sở dữ liệu (Data Access Layer)</em></summary>

- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`base_repo.py`](repositories/base_repo.py) — *Lớp cơ sở trừu tượng cung cấp các hàm CRUD cơ bản*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`behavior_event_repo.py`](repositories/behavior_event_repo.py) — *Lưu trữ dữ liệu tracking sự kiện và hành vi của người dùng*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`collection_repo.py`](repositories/collection_repo.py) — *Thực hiện các truy vấn liên quan đến bộ sưu tập địa điểm lưu trữ*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`conversation_repo.py`](repositories/conversation_repo.py) — *Lưu trữ và truy xuất các gói dữ liệu tin nhắn hội thoại Chatbot*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`hotel_repo.py`](repositories/hotel_repo.py) — *Quản lý dữ liệu thô và thông tin khách sạn từ cơ sở dữ liệu chính*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`invitation_repo.py`](repositories/invitation_repo.py) — *Lưu trữ và cập nhật trạng thái các lời mời cộng tác*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`notification_repo.py`](repositories/notification_repo.py) — *Ghi nhận danh sách thông báo hệ thống đẩy cho cá nhân*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`trip_repo.py`](repositories/trip_repo.py) — *Xử lý lưu trữ thông tin lịch trình và chi tiết các chuyến đi công tác/du lịch*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`upload_repo.py`](repositories/upload_repo.py) — *Quản lý thông tin và đường dẫn lưu trữ siêu dữ liệu (metadata) của tệp tải lên*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`user_repo.py`](repositories/user_repo.py) — *Truy xuất và xử lý dữ liệu tài khoản và phân quyền người dùng*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`view_repo.py`](repositories/view_repo.py) — *Ghi nhận cơ sở dữ liệu các lượt tương tác và thống kê xem bài đăng*

</details>

<details>
<summary>📁 <code>schemas</code>/ — <em>Định nghĩa định dạng dữ liệu, validation đầu vào và đầu ra qua Pydantic</em></summary>

- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`auth_schema.py`](schemas/auth_schema.py) — *Schema cho dữ liệu đăng nhập, đăng ký và Token hóa*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`chatbot_schema.py`](schemas/chatbot_schema.py) — *Schema định dạng request/response cho hội thoại AI*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`collection_schema.py`](schemas/collection_schema.py) — *Schema cấu trúc dữ liệu của bộ sưu tập địa điểm*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`conversation_schema.py`](schemas/conversation_schema.py) — *Schema lưu trữ cấu trúc gói tin nhắn hội thoại*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`discover_schema.py`](schemas/discover_schema.py) — *Schema định dạng dữ liệu đầu vào cho luồng xử lý khám phá địa điểm*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`hotel_ranking_schema.py`](schemas/hotel_ranking_schema.py) — *Schema lưu trữ trọng số và điểm số thuật toán xếp hạng khách sạn*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`invitation_schema.py`](schemas/invitation_schema.py) — *Schema định dạng thông tin lời mời nhóm*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`notification_schema.py`](schemas/notification_schema.py) — *Schema định dạng thông điệp đẩy và thông báo trạng thái*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`response_schema.py`](schemas/response_schema.py) — *Schema tiêu chuẩn cho cấu trúc phản hồi API hệ thống (Standard Response API)*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`serpapi_schema.py`](schemas/serpapi_schema.py) — *Schema validate dữ liệu thô lấy về từ SerpAPI Hotels*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`trip_context_schema.py`](schemas/trip_context_schema.py) — *Schema định cấu trúc ngữ cảnh của chuyến đi nhằm tối ưu hóa gợi ý*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`trip_schema.py`](schemas/trip_schema.py) — *Schema cấu trúc dữ liệu thông tin chi tiết của chuyến đi*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`upload_schema.py`](schemas/upload_schema.py) — *Schema validate thông tin phản hồi sau khi upload file thành công*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`user_behavior_schema.py`](schemas/user_behavior_schema.py) — *Schema cấu trúc hóa dữ liệu log hành vi người dùng gửi lên hệ thống*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`user_preference_schema.py`](schemas/user_preference_schema.py) — *Schema lưu trữ mô hình hóa sở thích du lịch cá nhân*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`user_schema.py`](schemas/user_schema.py) — *Schema định dạng thông tin hồ sơ tài khoản người dùng*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`vietmap_schema.py`](schemas/vietmap_schema.py) — *Schema định dạng dữ liệu trả về từ hệ thống VietMap*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`view_schema.py`](schemas/view_schema.py) — *Schema validate dữ liệu đếm lượt tương tác*

</details>

<details>
<summary>📁 <code>services</code>/ — <em>Tầng xử lý logic nghiệp vụ chính của ứng dụng (Business Logic Layer)</em></summary>

- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`auth_service.py`](services/auth_service.py) — *Logic nghiệp vụ mã hóa mật khẩu, tạo mã JWT và quản lý phiên*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`behavior_service.py`](services/behavior_service.py) — *Xử lý và phân tích log sự kiện hành vi để tìm hiểu xu hướng người dùng*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`chatbot_service.py`](services/chatbot_service.py) — *Xử lý hội thoại thông minh, lưu giữ ngữ cảnh hội thoại chatbot*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`collection_service.py`](services/collection_service.py) — *Logic nghiệp vụ liên quan đến tương tác, phân loại danh sách bộ sưu tập*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`conversation_service.py`](services/conversation_service.py) — *Quản lý vòng đời cuộc hội thoại và luồng tin nhắn trao đổi*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`discover_background_worker.py`](services/discover_background_worker.py) — *Tiến trình chạy ngầm xử lý phân tích và thu thập dữ liệu khám phá*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`discover_service.py`](services/discover_service.py) — *Logic trung tâm kết nối AI và API ngoài phục vụ luồng khám phá khách sạn*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`health_service.py`](services/health_service.py) — *Logic kiểm tra và đánh giá sức khỏe máy chủ cũng như kết nối DB/Cache*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`hotel_ranking_service.py`](services/hotel_ranking_service.py) — *Thuật toán tính toán điểm số và sắp xếp danh sách khách sạn*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`invitation_service.py`](services/invitation_service.py) — *Xử lý logic ràng buộc khi mời, chấp nhận hoặc rời nhóm lịch trình chung*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`notification_service.py`](services/notification_service.py) — *Logic xử lý đẩy thông báo Realtime hoặc qua Email/Hệ thống*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`semantic_encoder.py`](services/semantic_encoder.py) — *Chuyển đổi văn bản dữ liệu thô thành Vector Embedding tương ứng*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`sentiment_service.py`](services/sentiment_service.py) — *Xử lý phân tích sắc thái cảm xúc (Tích cực/Tiêu cực) của các bình luận khách sạn*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`summary_service.py`](services/summary_service.py) — *Sử dụng mô hình ngôn ngữ lớn để tóm tắt thông tin review khách sạn tự động*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`trip_service.py`](services/trip_service.py) — *Logic nghiệp vụ điều phối, sắp xếp và tối ưu hóa lịch trình chuyến đi*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`upload_service.py`](services/upload_service.py) — *Logic xử lý xác thực tệp, tạo presigned URL và đồng bộ với Cloudflare R2*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`user_service.py`](services/user_service.py) — *Logic nghiệp vụ chỉnh sửa thông tin người dùng và phân tích hành vi cơ bản*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`view_service.py`](services/view_service.py) — *Logic đếm, tổng hợp và xử lý bất đồng bộ dữ liệu lượt tương tác*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`weather_service.py`](services/weather_service.py) — *Xử lý dữ liệu thời tiết thực tế để hỗ trợ chấm điểm độ phù hợp của lịch trình*

</details>

<details>
<summary>📁 <code>utils</code>/ — <em>Các module tiện ích trợ giúp xử lý dữ liệu chung</em></summary>

- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`beauty_json.py`](utils/beauty_json.py) — *Định dạng và làm đẹp cấu trúc dữ liệu JSON khi ghi log*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`haversine_distance.py`](utils/haversine_distance.py) — *Công thức toán học tính toán khoảng cách địa lý dựa trên tọa độ GPS*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`parse_expiration_date.py`](utils/parse_expiration_date.py) — *Tiện ích phân tích và validate thời hạn hiệu lực của Token hoặc URL*

</details>

- 📄 `.env.example` — *File cấu hình mẫu chứa danh sách các biến môi trường cần thiết*
- 📄 `.gitignore` — *Danh sách các file và thư mục mà Git cần bỏ qua không tracking*
- <img src="https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg" width="14" /> [`main.py`](main.py) — *Điểm chạy (Entrypoint) chính khởi tạo ứng dụng FastAPI và nạp Middleware*
- 📄 `requirements.txt` — *Danh sách toàn bộ thư viện Python và các phiên bản phụ thuộc cần cài đặt*

---

## Hướng dẫn cài đặt

> [!IMPORTANT]
> Đảm bảo đã có đủ các API key bên dưới trước khi chạy. Thiếu bất kỳ key nào có thể khiến một số tính năng không hoạt động.

### Yêu cầu

<img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/Firebase-Firestore%20enabled-FFCA28?style=flat-square&logo=firebase&logoColor=black" />
<img src="https://img.shields.io/badge/Redis-tuỳ%20chọn-DC382D?style=flat-square&logo=redis&logoColor=white" />

### Các bước cài đặt

```bash
# 1. Clone repository
git clone https://github.com/HauBaka/T04_TDTT.git
cd T04_TDTT

# 2. Tạo môi trường ảo
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Cài đặt thư viện
pip install -r requirements.txt

# 4. Cấu hình môi trường
cp .env.example .env
# Điền các giá trị vào file .env (xem mục bên dưới)

# 5. Khởi động server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Cấu hình `.env`

```dotenv
# SerpApi
SERP_API_KEY=your_serp_api_key_here

# Firebase
FIREBASE_CREDENTIAL=your_firebase_credential_file.json

# Gemini
GEMINI_API_KEY=your_gemini_api_key_here

# VietMap
VIETMAP_API_KEY=your_vietmap_api_key_here
GEOHASH_PRECISION=5

# Hotel data
HOTEL_DATA_EXPIRE_DAYS=30

# R2
R2_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=your_r2_access_key
R2_SECRET_ACCESS_KEY=your_r2_secret_key
R2_BUCKET=your_bucket
R2_REGION=auto
R2_PUBLIC_CDN=your_cdn_url

# Upload policy
R2_PRESIGN_EXPIRE_SECONDS=300
R2_MAX_FILE_SIZE_MB=10
R2_ALLOWED_IMAGE_MIME_TYPES=image/jpeg,image/png,image/webp,image/gif
UPLOAD_PENDING_TTL_MINUTES=30
```

---

## Thành viên Backend

<table width="100%" style="border-collapse: collapse;">
  <tr>
    <td width="50%" valign="top" style="padding: 15px; border: 1px solid #30363d;">
      <table style="border: none; margin: 0; padding: 0;">
        <tr>
          <td valign="middle" style="border: none; padding: 0 12px 0 0;">
            <img src="https://images.weserv.nl/?url=github.com/HauBaka.png&w=70&h=70&mask=circle" width="70" height="70" />
          </td>
          <td valign="middle" style="border: none; padding: 0; line-height: 1.4;">
            <strong style="font-size: 16px; color: #58a6ff;">Vòng Sau Hậu</strong><br/>
            <a href="https://github.com/HauBaka" style="font-size: 13px; color: #8b949e; text-decoration: none;">@HauBaka</a><br/>
            <span style="font-size: 13px; color: #8b949e;">24120307</span>
          </td>
        </tr>
      </table>
      <p style="font-size: 13.5px; color: #c9d1d9; margin-top: 12px; line-height: 1.5; text-align: justify;">
        Trưởng nhóm Backend. Xây dựng kiến trúc lõi, tích hợp tính năng và review/merge Pull Request. Phụ trách backend core ở các tầng API, dịch vụ (services), truy xuất dữ liệu (repositories) và thiết kế schema.
      </p>
    </td>
    <td width="50%" valign="top" style="padding: 15px; border: 1px solid #30363d;">
      <table style="border: none; margin: 0; padding: 0;">
        <tr>
          <td valign="middle" style="border: none; padding: 0 12px 0 0;">
            <img src="https://images.weserv.nl/?url=github.com/tuan0306.png&w=70&h=70&mask=circle" width="70" height="70" />
          </td>
          <td valign="middle" style="border: none; padding: 0; line-height: 1.4;">
            <strong style="font-size: 16px; color: #58a6ff;">Nguyễn Đình Tuấn</strong><br/>
            <a href="https://github.com/tuan0306" style="font-size: 13px; color: #8b949e; text-decoration: none;">@tuan0306</a><br/>
            <span style="font-size: 13px; color: #8b949e;">24120237</span>
          </td>
        </tr>
      </table>
      <p style="font-size: 13.5px; color: #c9d1d9; margin-top: 12px; line-height: 1.5; text-align: justify;">
        AI Engineer. Làm pipeline AI, tối ưu thuật toán xếp hạng khách sạn, tóm tắt nội dung và phân tích cảm xúc. Đảm nhiệm các module liên quan đến hệ thống gợi ý và xử lý ngôn ngữ cho chatbot.
      </p>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top" style="padding: 15px; border: 1px solid #30363d;">
      <table style="border: none; margin: 0; padding: 0;">
        <tr>
          <td valign="middle" style="border: none; padding: 0 12px 0 0;">
            <img src="https://images.weserv.nl/?url=github.com/DTDuong275.png&w=70&h=70&mask=circle" width="70" height="70" />
          </td>
          <td valign="middle" style="border: none; padding: 0; line-height: 1.4;">
            <strong style="font-size: 16px; color: #58a6ff;">Dương Danh Toàn</strong><br/>
            <a href="https://github.com/DTDuong275" style="font-size: 13px; color: #8b949e; text-decoration: none;">@DTDuong275</a><br/>
            <span style="font-size: 13px; color: #8b949e;">24120230</span>
          </td>
        </tr>
      </table>
      <p style="font-size: 13.5px; color: #c9d1d9; margin-top: 12px; line-height: 1.5; text-align: justify;">
        Đảm nhiệm mảng hội thoại, xác thực (Authentication) và quản lý người dùng. Xử lý luồng đăng nhập, bảo mật và đảm bảo các tương tác cơ bản của người dùng trên hệ thống diễn ra thông suốt.
      </p>
    </td>
    <td width="50%" valign="top" style="padding: 15px; border: 1px solid #30363d;">
      <table style="border: none; margin: 0; padding: 0;">
        <tr>
          <td valign="middle" style="border: none; padding: 0 12px 0 0;">
            <img src="https://images.weserv.nl/?url=github.com/Ponnef.png&w=70&h=70&mask=circle" width="70" height="70" />
          </td>
          <td valign="middle" style="border: none; padding: 0; line-height: 1.4;">
            <strong style="font-size: 16px; color: #58a6ff;">Nguyễn Huỳnh Gia Bảo</strong><br/>
            <a href="https://github.com/Ponnef" style="font-size: 13px; color: #8b949e; text-decoration: none;">@Ponnef</a><br/>
            <span style="font-size: 13px; color: #8b949e;">24120264</span>
          </td>
        </tr>
      </table>
      <p style="font-size: 13.5px; color: #c9d1d9; margin-top: 12px; line-height: 1.5; text-align: justify;">
        Phụ trách domain chuyến đi (Trip) và theo dõi hành vi người dùng. Triển khai tính năng quản lý lịch trình, hồ sơ và xử lý đồng bộ dữ liệu hành vi để phục vụ cho hệ thống cá nhân hóa.
      </p>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top" style="padding: 15px; border: 1px solid #30363d;">
      <table style="border: none; margin: 0; padding: 0;">
        <tr>
          <td valign="middle" style="border: none; padding: 0 12px 0 0;">
            <img src="https://images.weserv.nl/?url=github.com/nhatduy2401.png&w=70&h=70&mask=circle" width="70" height="70" />
          </td>
          <td valign="middle" style="border: none; padding: 0; line-height: 1.4;">
            <strong style="font-size: 16px; color: #58a6ff;">Trần Lâm Nhật Duy</strong><br/>
            <a href="https://github.com/nhatduy2401" style="font-size: 13px; color: #8b949e; text-decoration: none;">@nhatduy2401</a><br/>
            <span style="font-size: 13px; color: #8b949e;">24120297</span>
          </td>
        </tr>
      </table>
      <p style="font-size: 13.5px; color: #c9d1d9; margin-top: 12px; line-height: 1.5; text-align: justify;">
        Phát triển các module lời mời, thông báo và bộ sưu tập (Collection). Xây dựng cơ chế kết nối cộng tác, giúp người dùng dễ dàng mời nhau tham gia chung vào các chuyến đi hoặc chia sẻ bộ sưu tập.
      </p>
    </td>
    <td width="50%" valign="top" style="border: none; background: transparent;"></td>
  </tr>
</table>

---

<div align="center">

<img src="https://img.shields.io/badge/Nhóm%2004-CSC10014-1a1a2e?style=for-the-badge" />
<img src="https://img.shields.io/badge/KHTN-ĐHQG--HCM-003087?style=for-the-badge" />

</div>