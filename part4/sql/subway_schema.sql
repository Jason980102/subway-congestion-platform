--
-- PostgreSQL database dump
--

\restrict X9afAvE81Amkzkc3CAAjn4RRIQofp5Bbo70PVjzhdBPGT4V9OPURPy3nVnteGTS

-- Dumped from database version 18.4
-- Dumped by pg_dump version 18.4

-- Started on 2026-08-12 21:37:42

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 224 (class 1259 OID 16423)
-- Name: event; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.event (
    event_id integer NOT NULL,
    event_name character varying(200) NOT NULL,
    event_type character varying(100),
    location character varying(200),
    start_time timestamp without time zone NOT NULL,
    end_time timestamp without time zone NOT NULL,
    expected_attendance integer,
    CONSTRAINT event_check CHECK ((end_time >= start_time)),
    CONSTRAINT event_expected_attendance_check CHECK ((expected_attendance >= 0))
);


ALTER TABLE public.event OWNER TO postgres;

--
-- TOC entry 223 (class 1259 OID 16422)
-- Name: event_event_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.event_event_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.event_event_id_seq OWNER TO postgres;

--
-- TOC entry 5122 (class 0 OID 0)
-- Dependencies: 223
-- Name: event_event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.event_event_id_seq OWNED BY public.event.event_id;


--
-- TOC entry 228 (class 1259 OID 16462)
-- Name: ridership; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ridership (
    ridership_id integer NOT NULL,
    station_id integer NOT NULL,
    record_date date NOT NULL,
    passenger_count integer,
    peak_hour boolean DEFAULT false,
    transit_timestamp timestamp without time zone,
    transfers integer DEFAULT 0,
    hour integer,
    day_of_week integer,
    month integer,
    is_weekend boolean DEFAULT false,
    congestion_level character varying(20),
    CONSTRAINT ridership_passenger_count_check CHECK ((passenger_count >= 0))
);


ALTER TABLE public.ridership OWNER TO postgres;

--
-- TOC entry 222 (class 1259 OID 16413)
-- Name: station; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.station (
    station_id integer NOT NULL,
    station_name character varying(100) NOT NULL,
    latitude numeric(9,6),
    longitude numeric(9,6),
    borough character varying(50),
    accessibility boolean DEFAULT false,
    mta_complex_id integer,
    daytime_routes character varying(100)
);


ALTER TABLE public.station OWNER TO postgres;

--
-- TOC entry 239 (class 1259 OID 16551)
-- Name: mv_station_daily_summary; Type: MATERIALIZED VIEW; Schema: public; Owner: postgres
--

CREATE MATERIALIZED VIEW public.mv_station_daily_summary AS
 SELECT s.station_id,
    s.station_name,
    r.record_date,
    sum(r.passenger_count) AS total_passengers,
    avg(r.passenger_count) AS avg_passengers
   FROM (public.station s
     JOIN public.ridership r ON ((s.station_id = r.station_id)))
  GROUP BY s.station_id, s.station_name, r.record_date
  WITH NO DATA;


ALTER MATERIALIZED VIEW public.mv_station_daily_summary OWNER TO postgres;

--
-- TOC entry 230 (class 1259 OID 16479)
-- Name: prediction; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.prediction (
    prediction_id integer NOT NULL,
    station_id integer NOT NULL,
    event_id integer,
    prediction_time timestamp without time zone NOT NULL,
    congestion_level character varying(20),
    confidence_score numeric(4,3),
    CONSTRAINT prediction_confidence_score_check CHECK (((confidence_score >= (0)::numeric) AND (confidence_score <= (1)::numeric))),
    CONSTRAINT prediction_congestion_level_check CHECK (((congestion_level)::text = ANY ((ARRAY['Low'::character varying, 'Medium'::character varying, 'High'::character varying])::text[])))
);


ALTER TABLE public.prediction OWNER TO postgres;

--
-- TOC entry 229 (class 1259 OID 16478)
-- Name: prediction_prediction_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.prediction_prediction_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.prediction_prediction_id_seq OWNER TO postgres;

--
-- TOC entry 5123 (class 0 OID 0)
-- Dependencies: 229
-- Name: prediction_prediction_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.prediction_prediction_id_seq OWNED BY public.prediction.prediction_id;


--
-- TOC entry 232 (class 1259 OID 16501)
-- Name: recommendation; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.recommendation (
    recommendation_id integer NOT NULL,
    prediction_id integer NOT NULL,
    recommended_route character varying(100),
    suggested_departure_time timestamp without time zone,
    incentive character varying(255)
);


ALTER TABLE public.recommendation OWNER TO postgres;

--
-- TOC entry 231 (class 1259 OID 16500)
-- Name: recommendation_recommendation_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.recommendation_recommendation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.recommendation_recommendation_id_seq OWNER TO postgres;

--
-- TOC entry 5124 (class 0 OID 0)
-- Dependencies: 231
-- Name: recommendation_recommendation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.recommendation_recommendation_id_seq OWNED BY public.recommendation.recommendation_id;


--
-- TOC entry 236 (class 1259 OID 16536)
-- Name: ridership_partitioned; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ridership_partitioned (
    ridership_id integer NOT NULL,
    station_id integer,
    record_date date,
    passenger_count integer
)
PARTITION BY RANGE (record_date);


ALTER TABLE public.ridership_partitioned OWNER TO postgres;

--
-- TOC entry 235 (class 1259 OID 16535)
-- Name: ridership_partitioned_ridership_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ridership_partitioned_ridership_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ridership_partitioned_ridership_id_seq OWNER TO postgres;

--
-- TOC entry 5125 (class 0 OID 0)
-- Dependencies: 235
-- Name: ridership_partitioned_ridership_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ridership_partitioned_ridership_id_seq OWNED BY public.ridership_partitioned.ridership_id;


--
-- TOC entry 237 (class 1259 OID 16541)
-- Name: ridership_2025; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ridership_2025 (
    ridership_id integer DEFAULT nextval('public.ridership_partitioned_ridership_id_seq'::regclass) CONSTRAINT ridership_partitioned_ridership_id_not_null NOT NULL,
    station_id integer,
    record_date date,
    passenger_count integer
);


ALTER TABLE public.ridership_2025 OWNER TO postgres;

--
-- TOC entry 238 (class 1259 OID 16546)
-- Name: ridership_2026; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ridership_2026 (
    ridership_id integer DEFAULT nextval('public.ridership_partitioned_ridership_id_seq'::regclass) CONSTRAINT ridership_partitioned_ridership_id_not_null NOT NULL,
    station_id integer,
    record_date date,
    passenger_count integer
);


ALTER TABLE public.ridership_2026 OWNER TO postgres;

--
-- TOC entry 227 (class 1259 OID 16461)
-- Name: ridership_ridership_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ridership_ridership_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ridership_ridership_id_seq OWNER TO postgres;

--
-- TOC entry 5126 (class 0 OID 0)
-- Dependencies: 227
-- Name: ridership_ridership_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ridership_ridership_id_seq OWNED BY public.ridership.ridership_id;


--
-- TOC entry 220 (class 1259 OID 16402)
-- Name: route; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.route (
    route_id integer NOT NULL,
    route_name character varying(20) NOT NULL,
    service_type character varying(30),
    description character varying(255)
);


ALTER TABLE public.route OWNER TO postgres;

--
-- TOC entry 219 (class 1259 OID 16401)
-- Name: route_route_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.route_route_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.route_route_id_seq OWNER TO postgres;

--
-- TOC entry 5127 (class 0 OID 0)
-- Dependencies: 219
-- Name: route_route_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.route_route_id_seq OWNED BY public.route.route_id;


--
-- TOC entry 221 (class 1259 OID 16412)
-- Name: station_station_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.station_station_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.station_station_id_seq OWNER TO postgres;

--
-- TOC entry 5128 (class 0 OID 0)
-- Dependencies: 221
-- Name: station_station_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.station_station_id_seq OWNED BY public.station.station_id;


--
-- TOC entry 226 (class 1259 OID 16438)
-- Name: trip; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.trip (
    trip_id integer NOT NULL,
    route_id integer NOT NULL,
    station_id integer NOT NULL,
    arrival_time timestamp without time zone NOT NULL,
    departure_time timestamp without time zone NOT NULL,
    trip_status character varying(30) DEFAULT 'Scheduled'::character varying,
    CONSTRAINT trip_check CHECK ((departure_time >= arrival_time))
);


ALTER TABLE public.trip OWNER TO postgres;

--
-- TOC entry 225 (class 1259 OID 16437)
-- Name: trip_trip_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.trip_trip_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.trip_trip_id_seq OWNER TO postgres;

--
-- TOC entry 5129 (class 0 OID 0)
-- Dependencies: 225
-- Name: trip_trip_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.trip_trip_id_seq OWNED BY public.trip.trip_id;


--
-- TOC entry 234 (class 1259 OID 16515)
-- Name: user_decision; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_decision (
    decision_id integer NOT NULL,
    recommendation_id integer NOT NULL,
    user_action character varying(20),
    decision_time timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT user_decision_user_action_check CHECK (((user_action)::text = ANY ((ARRAY['Accepted'::character varying, 'Rejected'::character varying, 'Ignored'::character varying, 'Followed'::character varying])::text[])))
);


ALTER TABLE public.user_decision OWNER TO postgres;

--
-- TOC entry 233 (class 1259 OID 16514)
-- Name: user_decision_decision_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.user_decision_decision_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_decision_decision_id_seq OWNER TO postgres;

--
-- TOC entry 5130 (class 0 OID 0)
-- Dependencies: 233
-- Name: user_decision_decision_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.user_decision_decision_id_seq OWNED BY public.user_decision.decision_id;


--
-- TOC entry 4908 (class 0 OID 0)
-- Name: ridership_2025; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ridership_partitioned ATTACH PARTITION public.ridership_2025 FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');


--
-- TOC entry 4909 (class 0 OID 0)
-- Name: ridership_2026; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ridership_partitioned ATTACH PARTITION public.ridership_2026 FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');


--
-- TOC entry 4913 (class 2604 OID 16426)
-- Name: event event_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.event ALTER COLUMN event_id SET DEFAULT nextval('public.event_event_id_seq'::regclass);


--
-- TOC entry 4920 (class 2604 OID 16482)
-- Name: prediction prediction_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.prediction ALTER COLUMN prediction_id SET DEFAULT nextval('public.prediction_prediction_id_seq'::regclass);


--
-- TOC entry 4921 (class 2604 OID 16504)
-- Name: recommendation recommendation_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.recommendation ALTER COLUMN recommendation_id SET DEFAULT nextval('public.recommendation_recommendation_id_seq'::regclass);


--
-- TOC entry 4916 (class 2604 OID 16465)
-- Name: ridership ridership_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ridership ALTER COLUMN ridership_id SET DEFAULT nextval('public.ridership_ridership_id_seq'::regclass);


--
-- TOC entry 4924 (class 2604 OID 16539)
-- Name: ridership_partitioned ridership_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ridership_partitioned ALTER COLUMN ridership_id SET DEFAULT nextval('public.ridership_partitioned_ridership_id_seq'::regclass);


--
-- TOC entry 4910 (class 2604 OID 16405)
-- Name: route route_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.route ALTER COLUMN route_id SET DEFAULT nextval('public.route_route_id_seq'::regclass);


--
-- TOC entry 4911 (class 2604 OID 16416)
-- Name: station station_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.station ALTER COLUMN station_id SET DEFAULT nextval('public.station_station_id_seq'::regclass);


--
-- TOC entry 4914 (class 2604 OID 16441)
-- Name: trip trip_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trip ALTER COLUMN trip_id SET DEFAULT nextval('public.trip_trip_id_seq'::regclass);


--
-- TOC entry 4922 (class 2604 OID 16518)
-- Name: user_decision decision_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_decision ALTER COLUMN decision_id SET DEFAULT nextval('public.user_decision_decision_id_seq'::regclass);


--
-- TOC entry 4943 (class 2606 OID 16436)
-- Name: event event_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.event
    ADD CONSTRAINT event_pkey PRIMARY KEY (event_id);


--
-- TOC entry 4955 (class 2606 OID 16489)
-- Name: prediction prediction_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.prediction
    ADD CONSTRAINT prediction_pkey PRIMARY KEY (prediction_id);


--
-- TOC entry 4958 (class 2606 OID 16508)
-- Name: recommendation recommendation_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.recommendation
    ADD CONSTRAINT recommendation_pkey PRIMARY KEY (recommendation_id);


--
-- TOC entry 4951 (class 2606 OID 16472)
-- Name: ridership ridership_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ridership
    ADD CONSTRAINT ridership_pkey PRIMARY KEY (ridership_id);


--
-- TOC entry 4935 (class 2606 OID 16409)
-- Name: route route_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.route
    ADD CONSTRAINT route_pkey PRIMARY KEY (route_id);


--
-- TOC entry 4937 (class 2606 OID 16411)
-- Name: route route_route_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.route
    ADD CONSTRAINT route_route_name_key UNIQUE (route_name);


--
-- TOC entry 4940 (class 2606 OID 16421)
-- Name: station station_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.station
    ADD CONSTRAINT station_pkey PRIMARY KEY (station_id);


--
-- TOC entry 4946 (class 2606 OID 16450)
-- Name: trip trip_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trip
    ADD CONSTRAINT trip_pkey PRIMARY KEY (trip_id);


--
-- TOC entry 4961 (class 2606 OID 16524)
-- Name: user_decision user_decision_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_decision
    ADD CONSTRAINT user_decision_pkey PRIMARY KEY (decision_id);


--
-- TOC entry 4944 (class 1259 OID 16532)
-- Name: idx_event_start_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_event_start_time ON public.event USING btree (start_time);


--
-- TOC entry 4953 (class 1259 OID 16533)
-- Name: idx_prediction_station_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_prediction_station_time ON public.prediction USING btree (station_id, prediction_time);


--
-- TOC entry 4956 (class 1259 OID 16534)
-- Name: idx_recommendation_prediction; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_recommendation_prediction ON public.recommendation USING btree (prediction_id);


--
-- TOC entry 4947 (class 1259 OID 16531)
-- Name: idx_ridership_station_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_ridership_station_date ON public.ridership USING btree (station_id, record_date);


--
-- TOC entry 4938 (class 1259 OID 16530)
-- Name: idx_station_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_station_name ON public.station USING btree (station_name);


--
-- TOC entry 4948 (class 1259 OID 16569)
-- Name: ix_ridership_congestion; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_ridership_congestion ON public.ridership USING btree (congestion_level);


--
-- TOC entry 4949 (class 1259 OID 16568)
-- Name: ix_ridership_timestamp; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_ridership_timestamp ON public.ridership USING btree (transit_timestamp);


--
-- TOC entry 4959 (class 1259 OID 16572)
-- Name: ix_user_decision_recommendation; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_decision_recommendation ON public.user_decision USING btree (recommendation_id);


--
-- TOC entry 4952 (class 1259 OID 16566)
-- Name: ux_ridership_station_timestamp; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ux_ridership_station_timestamp ON public.ridership USING btree (station_id, transit_timestamp);


--
-- TOC entry 4941 (class 1259 OID 16563)
-- Name: ux_station_mta_complex_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ux_station_mta_complex_id ON public.station USING btree (mta_complex_id);


--
-- TOC entry 4965 (class 2606 OID 16495)
-- Name: prediction fk_prediction_event; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.prediction
    ADD CONSTRAINT fk_prediction_event FOREIGN KEY (event_id) REFERENCES public.event(event_id);


--
-- TOC entry 4966 (class 2606 OID 16490)
-- Name: prediction fk_prediction_station; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.prediction
    ADD CONSTRAINT fk_prediction_station FOREIGN KEY (station_id) REFERENCES public.station(station_id);


--
-- TOC entry 4967 (class 2606 OID 16509)
-- Name: recommendation fk_recommendation_prediction; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.recommendation
    ADD CONSTRAINT fk_recommendation_prediction FOREIGN KEY (prediction_id) REFERENCES public.prediction(prediction_id);


--
-- TOC entry 4964 (class 2606 OID 16473)
-- Name: ridership fk_ridership_station; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ridership
    ADD CONSTRAINT fk_ridership_station FOREIGN KEY (station_id) REFERENCES public.station(station_id);


--
-- TOC entry 4962 (class 2606 OID 16451)
-- Name: trip fk_trip_route; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trip
    ADD CONSTRAINT fk_trip_route FOREIGN KEY (route_id) REFERENCES public.route(route_id);


--
-- TOC entry 4963 (class 2606 OID 16456)
-- Name: trip fk_trip_station; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trip
    ADD CONSTRAINT fk_trip_station FOREIGN KEY (station_id) REFERENCES public.station(station_id);


--
-- TOC entry 4968 (class 2606 OID 16525)
-- Name: user_decision fk_userdecision_recommendation; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_decision
    ADD CONSTRAINT fk_userdecision_recommendation FOREIGN KEY (recommendation_id) REFERENCES public.recommendation(recommendation_id);


-- Completed on 2026-08-12 21:37:42

--
-- PostgreSQL database dump complete
--

\unrestrict X9afAvE81Amkzkc3CAAjn4RRIQofp5Bbo70PVjzhdBPGT4V9OPURPy3nVnteGTS

