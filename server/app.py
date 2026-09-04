from env.api import app

def main():
    app.run(host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()