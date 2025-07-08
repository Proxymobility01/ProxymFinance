SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


CREATE TABLE `agences` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `agence_unique_id` varchar(255) NOT NULL,
  `nom_agence` varchar(255) NOT NULL,
  `nom_proprietaire` varchar(255) NOT NULL,
  `ville` varchar(255) NOT NULL,
  `quartier` varchar(255) DEFAULT NULL,
  `telephone` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  `password` varchar(255) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `logo` varchar(255) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table structure for table `association_user_motos`
--

CREATE TABLE `association_user_motos` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `validated_user_id` bigint(20) UNSIGNED NOT NULL,
  `moto_valide_id` bigint(20) UNSIGNED NOT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL,
  `deleted_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;



--
-- Table structure for table `batteries`
--

CREATE TABLE `batteries` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `batterie_unique_id` varchar(255) DEFAULT NULL,
  `mac_id` varchar(255) NOT NULL,
  `date_production` varchar(255) DEFAULT NULL,
  `gps` varchar(255) NOT NULL,
  `fabriquant` varchar(255) NOT NULL,
  `statut` varchar(255) NOT NULL DEFAULT 'en attente',
  `deleted_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


--
-- Table structure for table `batteries_valides`
--

CREATE TABLE `batteries_valides` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `batterie_unique_id` varchar(255) DEFAULT NULL,
  `mac_id` varchar(255) NOT NULL,
  `date_production` varchar(255) DEFAULT NULL,
  `gps` varchar(255) NOT NULL,
  `fabriquant` varchar(255) NOT NULL,
  `statut` varchar(255) NOT NULL DEFAULT 'en attente',
  `deleted_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;



--
-- Table structure for table `battery_agences`
--

CREATE TABLE `battery_agences` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `id_battery_valide` bigint(20) UNSIGNED NOT NULL,
  `id_agence` bigint(20) UNSIGNED NOT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `battery_agences`
--

--
-- Table structure for table `battery_distributeurs`
--

CREATE TABLE `battery_distributeurs` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `id_battery_valide` bigint(20) UNSIGNED NOT NULL,
  `id_distributeur` bigint(20) UNSIGNED NOT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Table structure for table `battery_entrepots`
--

CREATE TABLE `battery_entrepots` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `id_battery_valide` bigint(20) UNSIGNED NOT NULL,
  `id_entrepot` bigint(20) UNSIGNED NOT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Table structure for table `battery_moto_user_association`
--

CREATE TABLE `battery_moto_user_association` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `association_user_moto_id` bigint(20) UNSIGNED NOT NULL,
  `battery_id` bigint(20) UNSIGNED NOT NULL,
  `date_association` date DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;



-- --------------------------------------------------------

--
-- Table structure for table `bms_data`
--

CREATE TABLE `bms_data` (
  `id` int(11) NOT NULL,
  `mac_id` varchar(255) DEFAULT NULL,
  `state` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`state`)),
  `seting` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`seting`)),
  `longitude` decimal(10,0) DEFAULT NULL,
  `latitude` decimal(10,0) DEFAULT NULL,
  `timestamp` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;



--
-- Table structure for table `cache`
--

CREATE TABLE `cache` (
  `key` varchar(255) NOT NULL,
  `value` mediumtext NOT NULL,
  `expiration` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `cache_locks`
--

CREATE TABLE `cache_locks` (
  `key` varchar(255) NOT NULL,
  `owner` varchar(255) NOT NULL,
  `expiration` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `command_logs`
--

CREATE TABLE `command_logs` (
  `id` int(11) NOT NULL,
  `device_id` varchar(50) NOT NULL,
  `command` varchar(20) NOT NULL,
  `cmd_no` varchar(50) DEFAULT NULL,
  `response_message` text DEFAULT NULL,
  `status` enum('SUCCESS','FAILED') NOT NULL,
  `timestamp` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Table structure for table `confirmation_codes`
--

CREATE TABLE `confirmation_codes` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `user_id` bigint(20) UNSIGNED NOT NULL,
  `code` varchar(255) NOT NULL,
  `expires_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `devices`
--

CREATE TABLE `devices` (
  `id` int(11) NOT NULL,
  `objectid` varchar(255) NOT NULL,
  `platenumber` varchar(255) DEFAULT NULL,
  `fullName` varchar(255) DEFAULT NULL,
  `macid` varchar(255) DEFAULT NULL,
  `blockdate` varchar(255) DEFAULT NULL,
  `offline` tinyint(4) DEFAULT NULL,
  `speed` float DEFAULT NULL,
  `updtime` bigint(20) DEFAULT NULL,
  `defenceStatus` tinyint(4) DEFAULT NULL,
  `gpstime` bigint(20) DEFAULT NULL,
  `sim` varchar(255) DEFAULT NULL,
  `server_time` bigint(20) DEFAULT NULL,
  `macName` varchar(255) DEFAULT NULL,
  `gsm` int(11) DEFAULT NULL,
  `gpsCount` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `device_locations`
--

CREATE TABLE `device_locations` (
  `id` int(11) NOT NULL,
  `device_id` varchar(255) NOT NULL,
  `macid` varchar(255) NOT NULL,
  `longitude` float DEFAULT NULL,
  `latitude` float DEFAULT NULL,
  `speed` float DEFAULT NULL,
  `status` varchar(255) DEFAULT NULL,
  `update_time` bigint(20) DEFAULT NULL,
  `server_time` bigint(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


--
-- Table structure for table `distributeurs`
--

CREATE TABLE `distributeurs` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `distributeur_unique_id` varchar(255) NOT NULL,
  `nom` varchar(255) NOT NULL,
  `prenom` varchar(255) NOT NULL,
  `ville` varchar(255) NOT NULL,
  `quartier` varchar(255) DEFAULT NULL,
  `phone` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  `password` varchar(255) NOT NULL,
  `photo` varchar(255) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


--
-- Table structure for table `employes`
--

CREATE TABLE `employes` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `nom` varchar(255) NOT NULL,
  `prenom` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  `phone` varchar(255) NOT NULL,
  `password` varchar(255) NOT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL,
  `deleted_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- Table structure for table `entrepots`
--

CREATE TABLE `entrepots` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `entrepot_unique_id` varchar(255) NOT NULL,
  `nom_entrepot` varchar(255) NOT NULL,
  `nom_proprietaire` varchar(255) NOT NULL,
  `ville` varchar(255) NOT NULL,
  `quartier` varchar(255) DEFAULT NULL,
  `telephone` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  `password` varchar(255) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `logo` varchar(255) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `entrepots`

--
-- Table structure for table `failed_jobs`
--

CREATE TABLE `failed_jobs` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `uuid` varchar(255) NOT NULL,
  `connection` text NOT NULL,
  `queue` text NOT NULL,
  `payload` longtext NOT NULL,
  `exception` longtext NOT NULL,
  `failed_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `gps`
--

CREATE TABLE `gps` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `imei` varchar(255) NOT NULL,
  `latitude` decimal(10,7) DEFAULT NULL,
  `longitude` decimal(10,7) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `historique_agences`
--

CREATE TABLE `historique_agences` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `id_agence` bigint(20) UNSIGNED NOT NULL,
  `id_entrepot` bigint(20) UNSIGNED DEFAULT NULL,
  `id_distributeur` bigint(20) UNSIGNED DEFAULT NULL,
  `bat_sortante` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`bat_sortante`)),
  `bat_entrante` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`bat_entrante`)),
  `type_swap` enum('livraison','retour') NOT NULL,
  `id_user_entrepot` bigint(20) UNSIGNED DEFAULT NULL,
  `date_time` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--

--
-- Table structure for table `historique_entrepots`
--

CREATE TABLE `historique_entrepots` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `id_entrepot` bigint(20) UNSIGNED NOT NULL,
  `id_distributeur` bigint(20) UNSIGNED DEFAULT NULL,
  `bat_sortante` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`bat_sortante`)),
  `bat_entrante` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`bat_entrante`)),
  `type_swap` enum('livraison','retour') NOT NULL,
  `id_agence` bigint(20) UNSIGNED DEFAULT NULL,
  `id_user_entrepot` varchar(255) NOT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


--
-- Table structure for table `jobs`
--

CREATE TABLE `jobs` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `queue` varchar(255) NOT NULL,
  `payload` longtext NOT NULL,
  `attempts` tinyint(3) UNSIGNED NOT NULL,
  `reserved_at` int(10) UNSIGNED DEFAULT NULL,
  `available_at` int(10) UNSIGNED NOT NULL,
  `created_at` int(10) UNSIGNED NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `job_batches`
--

CREATE TABLE `job_batches` (
  `id` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `total_jobs` int(11) NOT NULL,
  `pending_jobs` int(11) NOT NULL,
  `failed_jobs` int(11) NOT NULL,
  `failed_job_ids` longtext NOT NULL,
  `options` mediumtext DEFAULT NULL,
  `cancelled_at` int(11) DEFAULT NULL,
  `created_at` int(11) NOT NULL,
  `finished_at` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `migrations`
--

CREATE TABLE `migrations` (
  `id` int(10) UNSIGNED NOT NULL,
  `migration` varchar(255) NOT NULL,
  `batch` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `motos`
--

CREATE TABLE `motos` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `vin` varchar(255) NOT NULL,
  `moto_unique_id` varchar(255) DEFAULT NULL,
  `model` varchar(255) NOT NULL,
  `gps_imei` varchar(255) NOT NULL,
  `statut` varchar(255) NOT NULL DEFAULT 'en attente',
  `deleted_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- Table structure for table `motos_valides`
--

CREATE TABLE `motos_valides` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `vin` varchar(255) NOT NULL,
  `moto_unique_id` varchar(255) DEFAULT NULL,
  `model` varchar(255) NOT NULL,
  `gps_imei` varchar(255) NOT NULL,
  `assurance` varchar(255) DEFAULT NULL,
  `permis` varchar(255) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- Table structure for table `password_reset_tokens`
--

CREATE TABLE `password_reset_tokens` (
  `email` varchar(255) NOT NULL,
  `token` varchar(255) NOT NULL,
  `created_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `pending_users`
--

CREATE TABLE `pending_users` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `user_unique_id` varchar(255) DEFAULT NULL,
  `nom` varchar(255) NOT NULL,
  `prenom` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  `phone` varchar(255) NOT NULL,
  `status` varchar(255) NOT NULL DEFAULT 'pending',
  `password` varchar(255) DEFAULT NULL,
  `token` varchar(255) DEFAULT NULL,
  `numero_cni` varchar(255) DEFAULT NULL,
  `photo_cni_recto` varchar(255) DEFAULT NULL,
  `photo_cni_verso` varchar(255) DEFAULT NULL,
  `photo` varchar(255) DEFAULT NULL,
  `link_expiration` timestamp NULL DEFAULT NULL,
  `verification_code` varchar(255) DEFAULT NULL,
  `verification_code_sent_at` timestamp NULL DEFAULT NULL,
  `completed_at` timestamp NULL DEFAULT NULL,
  `deleted_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `personal_access_tokens`
--

CREATE TABLE `personal_access_tokens` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `tokenable_type` varchar(255) NOT NULL,
  `tokenable_id` bigint(20) UNSIGNED NOT NULL,
  `name` varchar(255) NOT NULL,
  `token` varchar(64) NOT NULL,
  `abilities` text DEFAULT NULL,
  `last_used_at` timestamp NULL DEFAULT NULL,
  `expires_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `roles`
--

CREATE TABLE `roles` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `title` varchar(255) NOT NULL,
  `description` varchar(255) DEFAULT '',
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `role_entites`
--

CREATE TABLE `role_entites` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `title` varchar(255) NOT NULL,
  `description` text DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;



--
-- Table structure for table `sessions`
--

CREATE TABLE `sessions` (
  `id` varchar(255) NOT NULL,
  `user_id` bigint(20) UNSIGNED DEFAULT NULL,
  `ip_address` varchar(45) DEFAULT NULL,
  `user_agent` text DEFAULT NULL,
  `payload` longtext NOT NULL,
  `last_activity` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


--
-- Table structure for table `swaps`
--

CREATE TABLE `swaps` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `battery_moto_user_association_id` bigint(20) UNSIGNED NOT NULL,
  `battery_in_id` bigint(20) UNSIGNED NOT NULL,
  `battery_out_id` bigint(20) UNSIGNED NOT NULL,
  `swap_price` decimal(8,2) DEFAULT NULL,
  `swap_date` timestamp NOT NULL DEFAULT current_timestamp(),
  `nom` varchar(255) DEFAULT NULL,
  `prenom` varchar(255) DEFAULT NULL,
  `phone` varchar(20) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL,
  `battery_out_soc` varchar(255) DEFAULT NULL,
  `battery_in_soc` varchar(255) DEFAULT NULL,
  `agent_user_id` bigint(20) UNSIGNED NOT NULL,
  `id_agence` bigint(20) UNSIGNED NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;



--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `name` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  `email_verified_at` timestamp NULL DEFAULT NULL,
  `password` varchar(255) NOT NULL,
  `two_factor_secret` text DEFAULT NULL,
  `two_factor_recovery_codes` text DEFAULT NULL,
  `two_factor_confirmed_at` timestamp NULL DEFAULT NULL,
  `remember_token` varchar(100) DEFAULT NULL,
  `current_team_id` bigint(20) UNSIGNED DEFAULT NULL,
  `profile_photo_path` varchar(2048) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `users_agences`
--

CREATE TABLE `users_agences` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `user_agence_unique_id` varchar(255) NOT NULL,
  `nom` varchar(255) NOT NULL,
  `prenom` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  `phone` varchar(255) NOT NULL,
  `password` varchar(255) NOT NULL,
  `ville` varchar(255) NOT NULL,
  `quartier` varchar(255) NOT NULL,
  `photo` varchar(255) DEFAULT NULL,
  `id_role_entite` bigint(20) UNSIGNED NOT NULL,
  `id_agence` bigint(20) UNSIGNED NOT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;



--
-- Table structure for table `users_entrepots`
--

CREATE TABLE `users_entrepots` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `users_entrepot_unique_id` varchar(255) NOT NULL,
  `nom` varchar(255) NOT NULL,
  `prenom` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  `phone` varchar(255) NOT NULL,
  `ville` varchar(255) NOT NULL,
  `quartier` varchar(255) NOT NULL,
  `password` varchar(255) NOT NULL,
  `photo` varchar(255) DEFAULT NULL,
  `id_role_entite` bigint(20) UNSIGNED NOT NULL,
  `id_entrepot` bigint(20) UNSIGNED NOT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


--
-- Table structure for table `validated_users`
--

CREATE TABLE `validated_users` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `user_unique_id` varchar(255) NOT NULL,
  `nom` varchar(255) NOT NULL,
  `prenom` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  `phone` varchar(255) NOT NULL,
  `status` varchar(255) NOT NULL DEFAULT 'pending',
  `password` varchar(255) DEFAULT NULL,
  `token` varchar(255) DEFAULT NULL,
  `numero_cni` varchar(255) DEFAULT NULL,
  `photo_cni_recto` varchar(255) DEFAULT NULL,
  `photo_cni_verso` varchar(255) DEFAULT NULL,
  `photo` varchar(255) DEFAULT NULL,
  `link_expiration` timestamp NULL DEFAULT NULL,
  `verification_code` varchar(255) DEFAULT NULL,
  `verification_code_sent_at` timestamp NULL DEFAULT NULL,
  `completed_at` timestamp NULL DEFAULT NULL,
  `deleted_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


--
-- Indexes for table `agences`
--
ALTER TABLE `agences`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `agences_agence_unique_id_unique` (`agence_unique_id`),
  ADD UNIQUE KEY `agences_telephone_unique` (`telephone`),
  ADD UNIQUE KEY `agences_email_unique` (`email`);

--
-- Indexes for table `association_user_motos`
--
ALTER TABLE `association_user_motos`
  ADD PRIMARY KEY (`id`),
  ADD KEY `association_user_motos_validated_user_id_foreign` (`validated_user_id`),
  ADD KEY `association_user_motos_moto_valide_id_foreign` (`moto_valide_id`);

--
-- Indexes for table `batteries`
--
ALTER TABLE `batteries`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `batteries_mac_id_unique` (`mac_id`),
  ADD UNIQUE KEY `batteries_batterie_unique_id_unique` (`batterie_unique_id`);

--
-- Indexes for table `batteries_valides`
--
ALTER TABLE `batteries_valides`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `batteries_valides_mac_id_unique` (`mac_id`),
  ADD UNIQUE KEY `batteries_valides_batterie_unique_id_unique` (`batterie_unique_id`);

--
-- Indexes for table `battery_agences`
--
ALTER TABLE `battery_agences`
  ADD PRIMARY KEY (`id`),
  ADD KEY `battery_agences_id_battery_valide_foreign` (`id_battery_valide`),
  ADD KEY `battery_agences_id_agence_foreign` (`id_agence`);

--
-- Indexes for table `battery_distributeurs`
--
ALTER TABLE `battery_distributeurs`
  ADD PRIMARY KEY (`id`),
  ADD KEY `battery_distributeurs_id_battery_valide_foreign` (`id_battery_valide`),
  ADD KEY `battery_distributeurs_id_distributeur_foreign` (`id_distributeur`);

--
-- Indexes for table `battery_entrepots`
--
ALTER TABLE `battery_entrepots`
  ADD PRIMARY KEY (`id`),
  ADD KEY `battery_entrepots_id_battery_valide_foreign` (`id_battery_valide`),
  ADD KEY `battery_entrepots_id_entrepot_foreign` (`id_entrepot`);

--
-- Indexes for table `battery_moto_user_association`
--
ALTER TABLE `battery_moto_user_association`
  ADD PRIMARY KEY (`id`),
  ADD KEY `battery_moto_user_association_association_user_moto_id_foreign` (`association_user_moto_id`),
  ADD KEY `battery_moto_user_association_battery_id_foreign` (`battery_id`);

--
-- Indexes for table `bms_data`
--
ALTER TABLE `bms_data`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `cache`
--
ALTER TABLE `cache`
  ADD PRIMARY KEY (`key`);

--
-- Indexes for table `cache_locks`
--
ALTER TABLE `cache_locks`
  ADD PRIMARY KEY (`key`);

--
-- Indexes for table `command_logs`
--
ALTER TABLE `command_logs`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `confirmation_codes`
--
ALTER TABLE `confirmation_codes`
  ADD PRIMARY KEY (`id`),
  ADD KEY `confirmation_codes_user_id_foreign` (`user_id`);

--
-- Indexes for table `devices`
--
ALTER TABLE `devices`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `macid` (`macid`);

--
-- Indexes for table `device_locations`
--
ALTER TABLE `device_locations`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `distributeurs`
--
ALTER TABLE `distributeurs`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `distributeurs_distributeur_unique_id_unique` (`distributeur_unique_id`),
  ADD UNIQUE KEY `distributeurs_telephone_unique` (`phone`),
  ADD UNIQUE KEY `distributeurs_email_unique` (`email`);

--
-- Indexes for table `employes`
--
ALTER TABLE `employes`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `employes_email_unique` (`email`),
  ADD UNIQUE KEY `employes_phone_unique` (`phone`);

--
-- Indexes for table `entrepots`
--
ALTER TABLE `entrepots`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `entrepots_entrepot_unique_id_unique` (`entrepot_unique_id`),
  ADD UNIQUE KEY `entrepots_telephone_unique` (`telephone`),
  ADD UNIQUE KEY `entrepots_email_unique` (`email`);

--
-- Indexes for table `failed_jobs`
--
ALTER TABLE `failed_jobs`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `failed_jobs_uuid_unique` (`uuid`);

--
-- Indexes for table `gps`
--
ALTER TABLE `gps`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `gps_imei_unique` (`imei`);

--
-- Indexes for table `historique_agences`
--
ALTER TABLE `historique_agences`
  ADD PRIMARY KEY (`id`),
  ADD KEY `historique_agences_id_agence_foreign` (`id_agence`),
  ADD KEY `historique_agences_id_distributeur_foreign` (`id_distributeur`),
  ADD KEY `historique_agences_bat_sortante_foreign` (`bat_sortante`(768)),
  ADD KEY `historique_agences_bat_entrante_foreign` (`bat_entrante`(768)),
  ADD KEY `historique_agences_id_user_entrepot_foreign` (`id_user_entrepot`),
  ADD KEY `idx_bat_sortante_agences` (`bat_sortante`(768)),
  ADD KEY `idx_bat_entrante_agences` (`bat_entrante`(768));

--
-- Indexes for table `historique_entrepots`
--
ALTER TABLE `historique_entrepots`
  ADD PRIMARY KEY (`id`),
  ADD KEY `historique_entrepots_id_entrepot_foreign` (`id_entrepot`),
  ADD KEY `historique_entrepots_id_distributeur_foreign` (`id_distributeur`),
  ADD KEY `historique_entrepots_bat_sortante_foreign` (`bat_sortante`(768)),
  ADD KEY `historique_entrepots_bat_entrante_foreign` (`bat_entrante`(768)),
  ADD KEY `historique_entrepots_id_agence_foreign` (`id_agence`),
  ADD KEY `historique_entrepots_id_user_entrepot_foreign` (`id_user_entrepot`),
  ADD KEY `idx_bat_sortante` (`bat_sortante`(768)),
  ADD KEY `idx_bat_entrante` (`bat_entrante`(768));

--
-- Indexes for table `jobs`
--
ALTER TABLE `jobs`
  ADD PRIMARY KEY (`id`),
  ADD KEY `jobs_queue_index` (`queue`);

--
-- Indexes for table `job_batches`
--
ALTER TABLE `job_batches`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `migrations`
--
ALTER TABLE `migrations`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `motos`
--
ALTER TABLE `motos`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `motos_vin_unique` (`vin`),
  ADD UNIQUE KEY `motos_moto_unique_id_unique` (`moto_unique_id`);

--
-- Indexes for table `motos_valides`
--
ALTER TABLE `motos_valides`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `motos_valides_vin_unique` (`vin`),
  ADD UNIQUE KEY `motos_valides_moto_unique_id_unique` (`moto_unique_id`);

--
-- Indexes for table `password_reset_tokens`
--
ALTER TABLE `password_reset_tokens`
  ADD PRIMARY KEY (`email`);

--
-- Indexes for table `pending_users`
--
ALTER TABLE `pending_users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `pending_users_email_unique` (`email`),
  ADD UNIQUE KEY `pending_users_phone_unique` (`phone`),
  ADD UNIQUE KEY `pending_users_user_unique_id_unique` (`user_unique_id`);

--
-- Indexes for table `personal_access_tokens`
--
ALTER TABLE `personal_access_tokens`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `personal_access_tokens_token_unique` (`token`),
  ADD KEY `personal_access_tokens_tokenable_type_tokenable_id_index` (`tokenable_type`,`tokenable_id`);

--
-- Indexes for table `roles`
--
ALTER TABLE `roles`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `role_entites`
--
ALTER TABLE `role_entites`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `sessions`
--
ALTER TABLE `sessions`
  ADD PRIMARY KEY (`id`),
  ADD KEY `sessions_user_id_index` (`user_id`),
  ADD KEY `sessions_last_activity_index` (`last_activity`);

--
-- Indexes for table `swaps`
--
ALTER TABLE `swaps`
  ADD PRIMARY KEY (`id`),
  ADD KEY `swaps_battery_moto_user_association_id_foreign` (`battery_moto_user_association_id`),
  ADD KEY `swaps_battery_in_id_foreign` (`battery_in_id`),
  ADD KEY `swaps_battery_out_id_foreign` (`battery_out_id`),
  ADD KEY `fk_agent_user` (`agent_user_id`),
  ADD KEY `fk_id_agence` (`id_agence`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `users_email_unique` (`email`);

--
-- Indexes for table `users_agences`
--
ALTER TABLE `users_agences`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `users_agences_user_agence_unique_id_unique` (`user_agence_unique_id`),
  ADD UNIQUE KEY `user_agence_unique_id` (`user_agence_unique_id`),
  ADD UNIQUE KEY `user_agence_unique_id_2` (`user_agence_unique_id`),
  ADD UNIQUE KEY `user_agence_unique_id_3` (`user_agence_unique_id`),
  ADD KEY `users_agences_id_role_entite_foreign` (`id_role_entite`),
  ADD KEY `users_agences_id_agence_foreign` (`id_agence`);

--
-- Indexes for table `users_entrepots`
--
ALTER TABLE `users_entrepots`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `users_entrepots_users_entrepot_unique_id_unique` (`users_entrepot_unique_id`),
  ADD KEY `users_entrepots_id_role_entite_foreign` (`id_role_entite`),
  ADD KEY `users_entrepots_id_entrepot_foreign` (`id_entrepot`);

--
-- Indexes for table `validated_users`
--
ALTER TABLE `validated_users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `validated_users_user_unique_id_unique` (`user_unique_id`),
  ADD UNIQUE KEY `validated_users_email_unique` (`email`),
  ADD UNIQUE KEY `validated_users_phone_unique` (`phone`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `agences`
--
ALTER TABLE `agences`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT for table `association_user_motos`
--
ALTER TABLE `association_user_motos`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `batteries`
--
ALTER TABLE `batteries`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=22;

--
-- AUTO_INCREMENT for table `batteries_valides`
--
ALTER TABLE `batteries_valides`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=16;

--
-- AUTO_INCREMENT for table `battery_agences`
--
ALTER TABLE `battery_agences`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=99;

--
-- AUTO_INCREMENT for table `battery_distributeurs`
--
ALTER TABLE `battery_distributeurs`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=25;

--
-- AUTO_INCREMENT for table `battery_entrepots`
--
ALTER TABLE `battery_entrepots`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=47;

--
-- AUTO_INCREMENT for table `battery_moto_user_association`
--
ALTER TABLE `battery_moto_user_association`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `bms_data`
--
ALTER TABLE `bms_data`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=181;

--
-- AUTO_INCREMENT for table `command_logs`
--
ALTER TABLE `command_logs`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `confirmation_codes`
--
ALTER TABLE `confirmation_codes`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `devices`
--
ALTER TABLE `devices`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=32;

--
-- AUTO_INCREMENT for table `device_locations`
--
ALTER TABLE `device_locations`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=125;

--
-- AUTO_INCREMENT for table `distributeurs`
--
ALTER TABLE `distributeurs`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `employes`
--
ALTER TABLE `employes`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT for table `entrepots`
--
ALTER TABLE `entrepots`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT for table `failed_jobs`
--
ALTER TABLE `failed_jobs`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `gps`
--
ALTER TABLE `gps`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `historique_agences`
--
ALTER TABLE `historique_agences`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=48;

--
-- AUTO_INCREMENT for table `historique_entrepots`
--
ALTER TABLE `historique_entrepots`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=62;

--
-- AUTO_INCREMENT for table `jobs`
--
ALTER TABLE `jobs`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `migrations`
--
ALTER TABLE `migrations`
  MODIFY `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=30;

--
-- AUTO_INCREMENT for table `motos`
--
ALTER TABLE `motos`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `motos_valides`
--
ALTER TABLE `motos_valides`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `pending_users`
--
ALTER TABLE `pending_users`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT for table `personal_access_tokens`
--
ALTER TABLE `personal_access_tokens`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `roles`
--
ALTER TABLE `roles`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `role_entites`
--
ALTER TABLE `role_entites`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT for table `swaps`
--
ALTER TABLE `swaps`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=24;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `users_agences`
--
ALTER TABLE `users_agences`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT for table `users_entrepots`
--
ALTER TABLE `users_entrepots`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- AUTO_INCREMENT for table `validated_users`
--
ALTER TABLE `validated_users`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `association_user_motos`
--
ALTER TABLE `association_user_motos`
  ADD CONSTRAINT `association_user_motos_moto_valide_id_foreign` FOREIGN KEY (`moto_valide_id`) REFERENCES `motos_valides` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `association_user_motos_validated_user_id_foreign` FOREIGN KEY (`validated_user_id`) REFERENCES `validated_users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `battery_agences`
--
ALTER TABLE `battery_agences`
  ADD CONSTRAINT `battery_agences_id_agence_foreign` FOREIGN KEY (`id_agence`) REFERENCES `agences` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `battery_agences_id_battery_valide_foreign` FOREIGN KEY (`id_battery_valide`) REFERENCES `batteries_valides` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `battery_distributeurs`
--
ALTER TABLE `battery_distributeurs`
  ADD CONSTRAINT `battery_distributeurs_id_battery_valide_foreign` FOREIGN KEY (`id_battery_valide`) REFERENCES `batteries_valides` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `battery_distributeurs_id_distributeur_foreign` FOREIGN KEY (`id_distributeur`) REFERENCES `distributeurs` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `battery_entrepots`
--
ALTER TABLE `battery_entrepots`
  ADD CONSTRAINT `battery_entrepots_id_battery_valide_foreign` FOREIGN KEY (`id_battery_valide`) REFERENCES `batteries_valides` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `battery_entrepots_id_entrepot_foreign` FOREIGN KEY (`id_entrepot`) REFERENCES `entrepots` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `battery_moto_user_association`
--
ALTER TABLE `battery_moto_user_association`
  ADD CONSTRAINT `battery_moto_user_association_association_user_moto_id_foreign` FOREIGN KEY (`association_user_moto_id`) REFERENCES `association_user_motos` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `battery_moto_user_association_battery_id_foreign` FOREIGN KEY (`battery_id`) REFERENCES `batteries_valides` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `confirmation_codes`
--
ALTER TABLE `confirmation_codes`
  ADD CONSTRAINT `confirmation_codes_user_id_foreign` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `historique_agences`
--
ALTER TABLE `historique_agences`
  ADD CONSTRAINT `historique_agences_id_agence_foreign` FOREIGN KEY (`id_agence`) REFERENCES `agences` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `historique_agences_id_distributeur_foreign` FOREIGN KEY (`id_distributeur`) REFERENCES `distributeurs` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `historique_agences_id_user_entrepot_foreign` FOREIGN KEY (`id_user_entrepot`) REFERENCES `users_entrepots` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `historique_entrepots`
--
ALTER TABLE `historique_entrepots`
  ADD CONSTRAINT `historique_entrepots_id_agence_foreign` FOREIGN KEY (`id_agence`) REFERENCES `agences` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `historique_entrepots_id_distributeur_foreign` FOREIGN KEY (`id_distributeur`) REFERENCES `distributeurs` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `historique_entrepots_id_entrepot_foreign` FOREIGN KEY (`id_entrepot`) REFERENCES `entrepots` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `swaps`
--
ALTER TABLE `swaps`
  ADD CONSTRAINT `fk_agent_user` FOREIGN KEY (`agent_user_id`) REFERENCES `users_agences` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `fk_id_agence` FOREIGN KEY (`id_agence`) REFERENCES `users_agences` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `swaps_battery_in_id_foreign` FOREIGN KEY (`battery_in_id`) REFERENCES `batteries_valides` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `swaps_battery_moto_user_association_id_foreign` FOREIGN KEY (`battery_moto_user_association_id`) REFERENCES `battery_moto_user_association` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `swaps_battery_out_id_foreign` FOREIGN KEY (`battery_out_id`) REFERENCES `batteries_valides` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `users_agences`
--
ALTER TABLE `users_agences`
  ADD CONSTRAINT `users_agences_id_agence_foreign` FOREIGN KEY (`id_agence`) REFERENCES `agences` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `users_agences_id_role_entite_foreign` FOREIGN KEY (`id_role_entite`) REFERENCES `role_entites` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `users_entrepots`
--
ALTER TABLE `users_entrepots`
  ADD CONSTRAINT `users_entrepots_id_entrepot_foreign` FOREIGN KEY (`id_entrepot`) REFERENCES `entrepots` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `users_entrepots_id_role_entite_foreign` FOREIGN KEY (`id_role_entite`) REFERENCES `role_entites` (`id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
