-- MySQL Workbench Forward Engineering

SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';

-- -----------------------------------------------------
-- Schema caninoslook
-- -----------------------------------------------------

-- -----------------------------------------------------
-- Schema caninoslook
-- -----------------------------------------------------
CREATE SCHEMA IF NOT EXISTS `caninoslook` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci ;
USE `caninoslook` ;

-- -----------------------------------------------------
-- Table `caninoslook`.`cliente`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `caninoslook`.`cliente` (
  `id_cliente` INT NOT NULL AUTO_INCREMENT,
  `nombres_cli` VARCHAR(30) NOT NULL,
  `apellidos_cli` VARCHAR(30) NOT NULL,
  `email_cli` VARCHAR(70) NOT NULL,
  `numero_cli` INT NOT NULL,
  `password` VARCHAR(128) NOT NULL,
  PRIMARY KEY (`id_cliente`))
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `caninoslook`.`canino`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `caninoslook`.`canino` (
  `id_canino` INT NOT NULL AUTO_INCREMENT,
  `nombre_can` VARCHAR(20) NOT NULL,
  `edad_can` INT NOT NULL,
  `raza_can` VARCHAR(15) NOT NULL,
  `peso_can` INT NOT NULL,
  `tamano_can` VARCHAR(10) NOT NULL,
  `cuidados_esp_can` TEXT(500) NULL,
  `cliente_id_cliente` INT NOT NULL,
  PRIMARY KEY (`id_canino`),
  INDEX `fk_canino_cliente1_idx` (`cliente_id_cliente` ASC) VISIBLE,
  CONSTRAINT `fk_canino_cliente1`
    FOREIGN KEY (`cliente_id_cliente`)
    REFERENCES `caninoslook`.`cliente` (`id_cliente`))
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `caninoslook`.`reserva`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `caninoslook`.`reserva` (
  `id_reserva` INT NOT NULL AUTO_INCREMENT,
  `servicio_res` VARCHAR(20) NOT NULL,
  `hora_res` TIME NOT NULL,
  `fecha_res` DATE NOT NULL,
  `medio_pago_res` VARCHAR(15) NOT NULL,
  `valor_res` INT NOT NULL,
  `confirm_pago_res` TINYINT(1) NOT NULL,
  `cliente_id_cliente` INT NOT NULL,
  `canino_id_canino` INT NOT NULL,
  PRIMARY KEY (`id_reserva`),
  INDEX `fk_reserva_cliente1_idx` (`cliente_id_cliente` ASC) VISIBLE,
  INDEX `fk_reserva_canino1_idx` (`canino_id_canino` ASC) VISIBLE,
  CONSTRAINT `fk_reserva_canino1`
    FOREIGN KEY (`canino_id_canino`)
    REFERENCES `caninoslook`.`canino` (`id_canino`),
  CONSTRAINT `fk_reserva_cliente1`
    FOREIGN KEY (`cliente_id_cliente`)
    REFERENCES `caninoslook`.`cliente` (`id_cliente`))
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `caninoslook`.`sesion`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `caninoslook`.`sesion` (
  `id_sesion` INT NOT NULL AUTO_INCREMENT,
  `asiste` TINYINT(1) NOT NULL,
  `comentarios_ses` TEXT(500) NULL,
  `hora_inicio_ses` TIME NULL DEFAULT NULL,
  `hora_termino_ses` TIME NULL DEFAULT NULL,
  `canino_id_canino` INT NOT NULL,
  `reserva_id_reserva` INT NOT NULL,
  PRIMARY KEY (`id_sesion`),
  INDEX `fk_sesion_canino1_idx` (`canino_id_canino` ASC) VISIBLE,
  INDEX `fk_sesion_reserva1_idx` (`reserva_id_reserva` ASC) VISIBLE,
  CONSTRAINT `fk_sesion_canino1`
    FOREIGN KEY (`canino_id_canino`)
    REFERENCES `caninoslook`.`canino` (`id_canino`),
  CONSTRAINT `fk_sesion_reserva1`
    FOREIGN KEY (`reserva_id_reserva`)
    REFERENCES `caninoslook`.`reserva` (`id_reserva`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;
