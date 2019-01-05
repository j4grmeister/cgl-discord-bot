import tornado.ioloop
import tornado.web
import os

class MainHandler(tornado.web.RequestHandler):
    def get():
        self.write("Hello World!")

def make_app():
    return tornado.web.Application([(r"/", MainHandler),])

app = make_app()
port = int(os.environ['PORT'])
app.listen(port)
print("listening to port %s" % port)
tornado.ioloop.IOLoop.current().start()
